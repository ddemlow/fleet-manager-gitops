#!/bin/sh

# Create custom HTML page from template with environment variables
cat > /usr/share/nginx/html/index.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>GitOps Demo - ${APP_NAME}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: ${APP_COLOR};
            color: white;
            text-align: center;
            padding: 50px;
        }
        .container {
            background-color: rgba(0,0,0,0.3);
            padding: 30px;
            border-radius: 10px;
            max-width: 600px;
            margin: 0 auto;
        }
        h1 { font-size: 2.5em; margin-bottom: 20px; }
        .info { font-size: 1.2em; margin: 10px 0; }
        .method { background-color: rgba(255,255,255,0.2); padding: 10px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>${APP_NAME}</h1>
        <div class="info">Container Name: ${CONTAINER_NAME}</div>
        <div class="info">Port: ${CONTAINER_PORT}</div>
        <div class="info">Deployment Method: ${DEPLOYMENT_METHOD}</div>
        <div class="info">Image Version: ${IMAGE_VERSION}</div>
        <div class="method">
            <strong>GitOps Demo</strong><br>
            This container was deployed using ${DEPLOYMENT_METHOD} method<br>
            Managed by FetchIt GitOps
        </div>
        <div class="info">
            <small>Last updated: $(date)</small>
        </div>
    </div>
</body>
</html>
EOF

# Start nginx
nginx -g "daemon off;"
