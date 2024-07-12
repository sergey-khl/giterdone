import boto3

# Initialize a session using Amazon SNS
sns_client = boto3.client("sns", region_name="ca-central-1")


# Send your sms message.
def sendSms(phone_number, message):
    try:
        response = sns_client.publish(PhoneNumber=phone_number, Message=message)
        print(f"Message sent! Message ID: {response['MessageId']}")
    except Exception as e:
        print(f"Error sending message: {str(e)}")
