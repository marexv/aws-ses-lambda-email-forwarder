import os
import boto3
import email
import json
import logging
import botocore

from typing import Dict, Tuple, List

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
ses_client = boto3.client('ses')

ADDRESS_FOR_FORWARDING = os.environ.get('addressForForwarding', '')
FORWARD_TO_ADDRESSES = os.environ.get('adressesToForward', '').split(',')


def parse_incoming_s3_notification(record: dict) -> Tuple[str, str]:
    """Get bucket name and object key from notification received from S3."""

    logger.info("Processing new record")
    
    try:
        s3_bucket_name = record["s3"]["bucket"]["name"]
        s3_object_key = record["s3"]["object"]["key"]

        logger.info(f"Mail location: {s3_bucket_name}/{s3_object_key}")
       
        return s3_bucket_name, s3_object_key

    except KeyError:
        logger.critical(
            f"Could not get mail location from record: {record}",
            exc_info=True
        )

        return None, None


def get_object_body_from_s3(s3_bucket_name: str, s3_object_key: str) -> str:
    """Get object body from S3 by usig bucket name and object key."""

    logger.info(f"Fetching mail {s3_bucket_name}/{s3_object_key} from s3")
    
    s3_object = s3_client.get_object(
        Bucket = s3_bucket_name,
        Key = s3_object_key)

    logger.debug(f"Object fetched: {s3_object}")

    s3_object_body = s3_object["Body"].read().decode('utf-8')

    logger.info("Successfully retrieved objects body (content)")

    return s3_object_body    


def parse_s3_objects_body_to_email(s3_object_body: str) -> Dict[str, str]:
    """Parse string data to email object and extract needed information."""

    email_object = email.message_from_string(s3_object_body)

    email_subject = email_object.get("Subject", "DEFAULT SUBJECT ADDED BY ME")
    logger.info(f"Mail Subject: {email_subject}")

    email_original_sender = email_object.get("From", "NO ORIGINAL SENDER")
    logger.info(f"Mail From: {email_original_sender}")

    email_cc = email_object.get("CC", '')
    email_cc_addr_tuples = email.utils.getaddresses([email_cc])
    email_cc_addr_string = [addr[1] for addr in email_cc_addr_tuples]
    logger.info(f"Mail CC: {email_cc_addr_string}")
    
    email_text = ""
    email_text_charset = ""
    email_html = ""
    email_html_charset = ""
    
    for part in email_object.walk():
        content_type = part.get_content_type()
        content_disp = part.get('Content-Disposition')

        if content_type == 'text/plain' and content_disp == None:
            logger.debug("Found plain text")
            email_text_charset = part.get('charset', 'UTF-8')
            email_text = email_text + '\n' + part.get_payload()
            logger.debug(f"Found text: {email_text}")
            logger.debug(f"Text Charset: {email_text_charset}")
        elif content_type == 'text/html':
            logger.debug("Found html text")
            email_html_charset = part.get('charset', 'UTF-8')
            email_html = email_html + '\n' + part.get_payload()
            logger.debug(f"Found html: {email_html}")
            logger.debug(f"Html Charset: {email_html_charset}")
        else: 
            continue
    
    # TODO: Migrate to data class with python 3.7
    parsed_mail_data = {
        "subject": email_subject,
        "text": email_text,
        "text_charset": email_text_charset,
        "html": email_text,
        "html_charset": email_html_charset,
        "original_sender": email_original_sender,
        "cc": email_cc_addr_string,
    }
    
    return parsed_mail_data


def forward_email(parsed_mail_data: Dict[str, str]) -> Dict[str, str]:
    """Creates new mail and forwards it."""

    subject = parsed_mail_data["subject"]
    text = parsed_mail_data["text"]
    text_charset = parsed_mail_data["text_charset"]
    html = parsed_mail_data["html"]
    html_charset = parsed_mail_data["html_charset"]
    original_sender = parsed_mail_data["original_sender"]
    email_cc_addresses = parsed_mail_data["cc"]

    reply_to_addresses = [original_sender] + email_cc_addresses

    response = ses_client.send_email(
        Source= ADDRESS_FOR_FORWARDING,
        Destination={
            'ToAddresses': FORWARD_TO_ADDRESSES,
        },
        Message={
            'Subject': {
                'Data': subject,
                'Charset': 'UTF-8'
            },
            'Body': {
                'Text': {
                    'Data': text,
                    'Charset': text_charset
                },
                'Html': {
                    'Data': html,
                    'Charset': html_charset
                }
            }
        },
        ReplyToAddresses=reply_to_addresses
    )

    return response


def lambda_handler(event, context):
    """Main function invoked by notification from S3."""
    
    logger.debug(event)
    
    try:
        records = event["Records"]
        logger.debug(records)
        
        # Usually there will be only one record. Iterate to be safe.
        for record in records:
            bucket_name, object_key = parse_incoming_s3_notification(record)

            if bucket_name == None or object_key == None:
                raise Exception("Can't find bucket or object")

            s3_object_body = get_object_body_from_s3(bucket_name, object_key)
            parsed_mail_data = parse_s3_objects_body_to_email(s3_object_body)
            response = forward_email(parsed_mail_data)

        return {
            'statusCode': 200,
            'body': response
        }

    except KeyError:
        logger.critical(
            f"Could not parse parsing failed: {event}", exc_info=True)
    except botocore.exceptions.ClientError:
        logger.critical(
            f"Client error, check your permissions (policies)",
            exc_info=True)
    except Exception:
        logger.critical(
            f"Execution failed. Exception encountered",
            exc_info=True)
    
    return {
        'statusCode': 500,
        'body': json.dumps("FAILED")
    }
