import os
import json
import base64
import requests
import boto3

API_BASE = "https://api.company-information.service.gov.uk"
API_KEY = os.environ.get("COMPANIES_HOUSE_API_KEY")

s3 = boto3.client("s3")
BUCKET = os.environ.get("DOCUMENT_BUCKET")  # set in Lambda env vars

def _auth_header():
    token = base64.b64encode(f"{API_KEY}:".encode()).decode()
    return {"Authorization": f"Basic {token}"}

def _json_response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }

def lambda_handler(event, context):
    path = event.get("path", "")
    query = event.get("queryStringParameters") or {}

    # Search companies
    if path.endswith("/search"):
        q = query.get("q", "")
        url = f"{API_BASE}/search/companies?q={q}&items_per_page=5"
        r = requests.get(url, headers=_auth_header())
        return _json_response(r.status_code, r.json())

    # Filing history
    if "/company/" in path and path.endswith("/filing-history"):
        company_number = path.split("/company/")[1].split("/filing-history")[0]
        url = f"{API_BASE}/company/{company_number}/filing-history?items_per_page=5"
        r = requests.get(url, headers=_auth_header())
        return _json_response(r.status_code, r.json())

    # Document download
    if "/document/" in path:
        document_id = path.split("/document/")[1]
        url = f"https://document-api.company-information.service.gov.uk/document/{document_id}"
        r = requests.get(url, headers=_auth_header())
        if r.status_code == 200:
            key = f"documents/{document_id}.pdf"
            s3.put_object(Bucket=BUCKET, Key=key, Body=r.content, ContentType="application/pdf")
            presigned = s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": key}, ExpiresIn=3600)
            return _json_response(200, {"url": presigned})
        return _json_response(r.status_code, {"error": r.text})

    return _json_response(404, {"error": "Route not found"})
