export const handler = async (event, context) => {
    console.log('Simple test handler - Event:', JSON.stringify(event, null, 2));
    
    try {
        const { requestContext, body } = event;
        const httpMethod = requestContext?.http?.method || 'GET';
        const path = requestContext?.http?.path || '/';
        
        const response = {
            statusCode: 200,
            headers: {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: 'SM Assistant API Gateway Test',
                status: 'working',
                path: path,
                method: httpMethod,
                timestamp: new Date().toISOString()
            })
        };
        
        console.log('Returning response:', JSON.stringify(response, null, 2));
        return response;
        
    } catch (error) {
        console.error('Error:', error);
        return {
            statusCode: 500,
            headers: {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                error: 'Internal server error',
                details: error.message
            })
        };
    }
};