export const handler = async (event) => {
    console.log('Event received:', JSON.stringify(event, null, 2));
    
    const path = event.requestContext?.http?.path || event.rawPath || '/';
    const method = event.requestContext?.http?.method || event.httpMethod || 'GET';
    
    const response = {
        statusCode: 200,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        body: JSON.stringify({
            message: 'SM Assistant API Gateway is working!',
            path: path,
            method: method,
            timestamp: new Date().toISOString(),
            status: 'healthy'
        })
    };
    
    console.log('Returning response:', JSON.stringify(response, null, 2));
    return response;
};