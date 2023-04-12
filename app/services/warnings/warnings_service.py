"""Module service working with warnings."""

import uuid
from datetime import datetime, timedelta, timezone

import boto3

from app.services.warnings.forcast_service import get_forcast_data
from app.services.warnings.models import Condition, WarningModel
from app.services.warnings.utils import find_closest_number
from config import get_config

c = get_config()


def add_warning(warning: WarningModel, user_id: str):
    """create warning item"""

    dynamodb_client = boto3.client("dynamodb")
    new_date = warning.warning_datetime.replace(
        minute=0, second=0, microsecond=0)
    new_date = new_date.replace(tzinfo=timezone.utc)

    item = {
        "id": {"S": str(uuid.uuid4())},
        "user_id": {"S": user_id},
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


def get_warnings(user_id: str):
    """get warnings list"""

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(c.WARNINGS_TABLE)
    resp = table.query(
        IndexName="user_id-index",
        KeyConditionExpression="user_id = :user_id",
        ExpressionAttributeValues={
            ":user_id": user_id,
        },
    )
    return resp["Items"]


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
        print("before_hour", before_hour)
        resp = table.query(
            IndexName="warning_datetime-index",
            KeyConditionExpression="warning_datetime = :date1",
            ExpressionAttributeValues={
                ":date1": str(before_hour),
            },
        )
        items += resp["Items"]

    return items


def update_warning_field(item_id: str, field: str, value: str):
    """update warning item field"""

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(c.WARNINGS_TABLE)

    table.update_item(
        Key={"id": item_id},
        UpdateExpression=f"set {field}=:value",
        ExpressionAttributeValues={":value": str(value)},
    )


def send_sms(number: str, text: str) -> bool:
    """send sms"""

    client = boto3.client("sns")
    response = client.publish(Message=text, PhoneNumber=number)
    print(response)
    return response["ResponseMetadata"]["HTTPStatusCode"] == 200


def send_email(recipient: str, body: str) -> bool:
    """send email"""

    ses = boto3.client("ses", region_name="us-east-1")

    sender = "no-reply@jua.ai"
    subject = "Jua warning"

    message = {"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}}

    response = ses.send_email(
        Source=sender, Destination={"ToAddresses": [recipient]}, Message=message
    )
    print("test", response)
    return response["ResponseMetadata"]["HTTPStatusCode"] == 200


def notify_warning(warning: dict, condition_result: bool, value: float):
    """notify users"""

    email_body = f"""
Warning: "{warning["name"]}"
Condition: {warning["condition"]}
Parameter: {warning["parameter"]}
Value:  {warning["value"]}
Result: {condition_result}
Real value: {value}
    """

    update_warning_field(
        item_id=warning["id"], field="email_body", value=email_body)

    sms_sent = send_sms(number=warning["phone_number"], text=email_body)

    email_sent = send_email(recipient=warning["email"], body=email_body)

    update_warning_field(
        item_id=warning["id"], field="sms_sent", value=str(sms_sent))
    update_warning_field(
        item_id=warning["id"], field="email_sent", value=str(email_sent)
    )


def check_warning_condition(warning: dict, forcast_data: dict) -> dict:
    """check whether zarr data matches with warning condition"""

    check_value = float(warning["value"])
    lon = float(warning["lon"])
    lat = float(warning["lat"])

    longitudes = forcast_data[warning["warning_datetime"]].keys()
    lon_closest = find_closest_number(lon, longitudes)
    latitudes = forcast_data[warning["warning_datetime"]][lon_closest].keys()
    latclosest = find_closest_number(lat, latitudes)

    value = forcast_data[warning["warning_datetime"]][lon_closest][latclosest][
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

    return {"result": result, "value": value, "warning": warning}


def check_warnings():
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

    data = get_forcast_data(
        parameters=parameters,
        coordinates=coordinates,
    )

    for warning in warnings:
        result: dict = check_warning_condition(
            warning=warning, forcast_data=data)
        notify_warning(
            warning=warning, condition_result=result["result"], value=result["value"]
        )
