"""
Debug version of the Lambda function to identify issues
"""
import json
import traceback
import os

def lambda_handler(event, context):
    """Simplified Lambda handler for debugging"""
    try:
        # Basic health check
        response_data = {
            "message": "SM Assistant Debug - Lambda Working",
            "status": "healthy",
            "environment": {
                "python_version": f"{context.get_remaining_time_in_millis()}" if context else "unknown",
                "aws_region": os.environ.get('AWS_REGION', 'unknown'),
                "function_name": context.function_name if context else 'unknown'
            },
            "environment_variables": {
                "AZURE_AI_PROJECT_CONNECTION_STRING": "SET" if os.environ.get('AZURE_AI_PROJECT_CONNECTION_STRING') else "MISSING",
                "AZURE_AI_PROJECT_NAME": "SET" if os.environ.get('AZURE_AI_PROJECT_NAME') else "MISSING",
                "AZURE_SUBSCRIPTION_ID": "SET" if os.environ.get('AZURE_SUBSCRIPTION_ID') else "MISSING",
                "AZURE_RESOURCE_GROUP_NAME": "SET" if os.environ.get('AZURE_RESOURCE_GROUP_NAME') else "MISSING"
            },
            "event_info": {
                "path": event.get('rawPath', 'unknown'),
                "method": event.get('requestContext', {}).get('http', {}).get('method', 'unknown'),
                "headers": list(event.get('headers', {}).keys())
            }
        }
        
        # Test basic imports
        try:
            import fastapi
            response_data["imports"] = {"fastapi": "OK"}
        except Exception as e:
            response_data["imports"] = {"fastapi": f"ERROR: {str(e)}"}
            
        try:
            import mangum
            response_data["imports"]["mangum"] = "OK"
        except Exception as e:
            response_data["imports"]["mangum"] = f"ERROR: {str(e)}"
            
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps(response_data, indent=2)
        }
        
    except Exception as e:
        error_response = {
            "error": "Lambda Debug Handler Failed",
            "message": str(e),
            "traceback": traceback.format_exc(),
            "event": event
        }
        
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(error_response, indent=2)
        }