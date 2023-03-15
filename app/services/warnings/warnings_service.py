"""Module service working with warnings."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from dateutil import parser

from app.services.data_zarr.data_service import DataService
from app.services.warnings.warning import Condition, WarningModel
from config import get_config

c = get_config()


def add_warning(warning: WarningModel):
    """create warning item"""

    dynamodb_client = boto3.client("dynamodb")
    new_date = warning.warning_datetime.replace(minute=0, second=0, microsecond=0)
    new_date = new_date.replace(tzinfo=timezone.utc)

    item = {
        "id": {"S": str(uuid.uuid4())},
        "parameter": {"S": warning.parameter},
        "email": {"S": warning.email},
        "name": {"S": warning.name},
        "location": {"S": warning.location},
        "warning_datetime": {"S": str(new_date)},
        "condition": {"S": warning.condition.value},
        "lon": {"N": str(warning.coordinates[0])},
        "lat": {"N": str(warning.coordinates[1])},
        "value": {"N": str(warning.value)},
        "phone_number": {"S": str(warning.phone_number)},
    }
    dynamodb_client.put_item(
        TableName=c.WARNINGS_TABLE,
        Item=item,
    )


def get_warnings():
    """get warnings list"""

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(c.WARNINGS_TABLE)
    response = table.scan()
    return response["Items"]


def delete_all():
    """delete all warnings"""

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(c.WARNINGS_TABLE)
    response = table.scan()

    with table.batch_writer() as batch:
        for each in response["Items"]:
            batch.delete_item(
                Key={
                    "id": each["id"],
                }
            )


def get_before_hours_warnings(hours: list[int]):
    """get warnings with date before hours"""

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(c.WARNINGS_TABLE)

    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    now = now.replace(tzinfo=timezone.utc)
    items = []
    for hour in hours:
        before_hour = now + timedelta(hours=hour)

        resp = table.query(
            IndexName="warning_datetime-index",
            KeyConditionExpression="warning_datetime = :date1",
            ExpressionAttributeValues={
                ":date1": str(before_hour),
            },
        )
        items += resp["Items"]

    return items


def get_data_as_map(data_service: DataService, date_range, parameters, coordinates):
    """Convert zarr data to the following format:
    "2023-03-14 04:00:00+00:00": {
        "71.42916665688892": {
            "51.1291666681783": {
                "DATETIME": "2023-03-14T04:00:00Z",
                "VAR_10U": -0.4781881272792816
            }
        },
        "76.94583332334105": {
            "43.23750000181853": {
                "DATETIME": "2023-03-14T04:00:00Z",
                "VAR_10U": 0.44463953375816345
            }
        }
    }
    """
    data = data_service.get_points_as_geojson(
        requested_params=parameters,
        coords=coordinates,
        date_range=date_range,
    )

    datamap: dict = {}
    features = data["features"]
    for item in features:
        coords = item["geometry"]["coordinates"]
        properties = item["properties"]
        warning_datetime = properties["DATETIME"]
        warning_datetime = parser.parse(warning_datetime).replace(tzinfo=timezone.utc)

        if str(warning_datetime) not in datamap:
            datamap[str(warning_datetime)] = {}

        if coords[0] not in datamap[str(warning_datetime)]:
            datamap[str(warning_datetime)][coords[0]] = {}

        datamap[str(warning_datetime)][coords[0]][coords[1]] = properties

    return datamap


def find_closest_number(value: float, values: list[float]) -> Optional[float]:
    """get closest to value number from values"""

    closest_value = None
    closest_distance = float("inf")
    for num in values:
        distance = abs(num - value)
        if distance < closest_distance:
            closest_distance = distance
            closest_value = num
    return closest_value


def check_warning_condition_hit(warning: dict, datamap: dict) -> dict:
    """check whether zarr data matches with warning condition"""

    check_value = float(warning["value"])
    lon = float(warning["lon"])
    lat = float(warning["lat"])

    longitudes = datamap[warning["warning_datetime"]].keys()
    lon_closest = find_closest_number(lon, longitudes)
    latitudes = datamap[warning["warning_datetime"]][lon_closest].keys()
    latclosest = find_closest_number(lat, latitudes)

    value = datamap[warning["warning_datetime"]][lon_closest][latclosest][
        warning["parameter"]
    ]

    result = False
    op_dict = {
        Condition.GREATER_THAN.value: check_value.__gt__,
        Condition.GREATER_THAN_E.value: check_value.__ge__,
        Condition.LESS_THAN.value: check_value.__lt__,
        Condition.LESS_THAN_E.value: check_value.__le__,
    }
    operation = op_dict[warning["condition"]]
    result = operation(value)

    return {"hit": result, "value": value}


def update_warning_field(item_id: str, field: str, field_type: str, value: str):
    """update warning item field"""

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(c.WARNINGS_TABLE)

    table.update_item(
        Key={"id": item_id},
        UpdateExpression=f"set {field}=:value",
        ExpressionAttributeValues={":value": {field_type: str(value)}},
    )


def send_sms(number: str, text: str) -> bool:
    """send sms"""

    client = boto3.client("sns")
    topic_arn = "arn:aws:sns:us-east-1:323677137491:warnings"
    client.subscribe(TopicArn=topic_arn, Protocol="sms", Endpoint=number)
    response = client.publish(Message=text, TopicArn=topic_arn)
    return response["ResponseMetadata"]["HTTPStatusCode"] == 200


def send_email(recipient: str, body: str) -> bool:
    """send email"""

    ses = boto3.client("ses", region_name="us-east-1")

    sender = "no-reply@jua.ai"
    subject = "Jua warning"

    message = {"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}}

    try:
        response = ses.send_email(
            Source=sender, Destination={"ToAddresses": [recipient]}, Message=message
        )
        return response["ResponseMetadata"]["HTTPStatusCode"] == 200
    except ClientError:
        return False


def notify_warning(warning: dict, condition_hit: bool, value: float):
    """send email"""

    email_body = f"""
Warning: "{warning["name"]}"
Condition: {warning["condition"]}
Parameter: {warning["parameter"]}
Value:  {warning["value"]}
Result: {condition_hit}
Real value: {value}
    """

    update_warning_field(
        item_id=warning["id"], field="email_body", field_type="S", value=email_body
    )

    sms_sent = send_sms(number=warning["phone_number"], text=email_body)

    email_sent = send_email(recipient=warning["email"], body=email_body)

    update_warning_field(
        item_id=warning["id"], field="sms_sent", field_type="S", value=str(sms_sent)
    )
    update_warning_field(
        item_id=warning["id"], field="email_sent", field_type="S", value=str(email_sent)
    )


def check_warnings(data_service: DataService, date_range):
    """load warnings to check condition and notify users"""

    warnings = get_before_hours_warnings([48, 12, 6])
    coordinates = [
        (float(warning["lon"]), float(warning["lat"])) for warning in warnings
    ]
    parameters = [warning["parameter"] for warning in warnings]

    coordinates = list(set(coordinates))
    parameters = list(set(parameters))

    if not coordinates:
        return
    datamap = get_data_as_map(
        data_service=data_service,
        date_range=date_range,
        parameters=parameters,
        coordinates=coordinates,
    )

    for warning in warnings:
        result: dict = check_warning_condition_hit(warning=warning, datamap=datamap)
        notify_warning(
            warning=warning, condition_hit=result["hit"], value=result["value"]
        )
