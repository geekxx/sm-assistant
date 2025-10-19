"""
Debug Lambda function to see the full event structure
"""
import json
from datetime import datetime

def lambda_handler(event, context):
    """Debug handler to see what's in the event"""
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'debug_info': {
                'full_event': event,
                'context_info': {
                    'function_name': context.function_name if hasattr(context, 'function_name') else 'unknown',
                    'aws_request_id': context.aws_request_id if hasattr(context, 'aws_request_id') else 'unknown'
                },
                'timestamp': datetime.now().isoformat()
            }
        }, indent=2)
    }