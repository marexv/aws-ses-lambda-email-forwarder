# aws-ses-lambda-email-forwarder

Serverless (Lambda) function that forwards mail received through AWS Simple 
Email Service to your existing inbox (tested with gmail). This function enables 
you to receive emails for your custom domains and subdomains and read them in 
apps you like and know for almost free (minimum cloud costs).

## Motivation

I wanted to be able to receive mails for mutiple custom email addresses, read them 
in gmail app and reply to them. This way I avoided cost of AWS workmail, Office 365 or G suite.
I am not stating that this is better than those apps but it runs virtually for free 
and cost of those services add up quickly if you want to run several things at once.

Using this approach you can have professionally looking website up in minutes
with all the popular emails like *hello@yourdomain.com*, *support@yourdomain.com*, etc ...

## Setup

### Function Policies and Roles
1. Create two new policies that will allow lambda to get and delete objects form S3 and send email. Use jsos files listed
    - `policies/read-and-delete-from-s3.json` (remeber the name you gave to s3, you will need it later, you can also come back and change it here)
    - `policies/send-email-and-raw-email.json` 
2. Create new execution role for lamda funciton
3. Add policies from abowe and `AWSLambdaBasicExecutionRole` to it (so 3 policies in total)

### Creating Function
1. Go to lambda console
2. Create new function with Python 3.6 environment
3. Use role created above 
4. Leave settings as is, function doesn't need a lot of resources
5. You can now simply copy & paste code into online editor
6. Create environment variables:
    - addressForForwarding (has to be validated address *e.g. forwarder@yourdomain.com*)
    - adressesToForward (Email of the inbox where you want to read your forwarded mails *e.g. john.doe@gmail.com*)

### Setting the Flow
1. Verify your domain in AWS SES by adding generated records to your DNS
2. Enable email receving and create first rule set
3. Add rule that forwards all mails sent to *yourdoman.com* to S3 bucket, when prompted for bucket name, click `create new bucket` this way bucket will automatically have all the necessary permissions so that SES can save mails to it. Use the name you used when setting *read-and-delete-from-s3* policy, or go back and add your new bucket to that policy.
4. Go to S3 (**I recomend you make sure this bucket stays private with blanket privacy policies that were added around November 2018**)
5. Go to properties tab
6. Set up new event
    - Events: `PUT`
    - Send to: `Lambda function`
    - Lambda:  `NAME OF THIS FUNCTION IN YOUR CLOUD`

Voila ... now when you send mails to any mail in *@yourdomain.com* they will be forwarded to adresses you provided in env variable *adressesToForward (e.g. john.doe@gmail.com)* . They should be imediately visible in your inbox and since function takes care of REPLY TO value you can instatnly continue conversation from your favourite app (client)

In gmail you can set up alias that will enable you to reply from *@yourdomain.com* email address. 

