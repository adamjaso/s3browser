# AWS S3 Bucket Browser

This project displays a minimal HTML table for browsing the files and directories
of an S3 bucket.

Each row in the HTML table of files and directories shows

- Last modified time (files only) as returned by S3
- Item size (files only) in bytes as returned by S3
- Download link (files only) that redirects to a presigned S3 url
- View link that returns a file as `text/plain`, or returns a directory as another table of files and directories
- S3 key name as returned by S3

The server uses `Flask` for it's HTTP server and `Boto3` as an AWS S3 client. All dependencies are listed in `requirements.txt`.

## Caveats

- The server provides no security mechanism as it is only intended as a local hosting convenience for browsing files in S3 via the browser.
- The server does not take any precaution to escape special HTML characters used in S3 keys.

## Configuration

The server is configured using environment variables.

| Name | Description |
| --- | --- |
| AWS_ACCESS_KEY_ID | An AWS access key ID that is authorized to access the S3 bucket
| AWS_SECRET_ACCESS_KEY | An AWS secret access key that is authorized to access the S3 bucket
| S3_BUCKET | The target AWS S3 bucket
