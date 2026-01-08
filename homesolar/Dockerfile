ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    nginx

# Create app directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY rootfs /
COPY app /app

# Set permissions
RUN chmod +x /run.sh

# Expose port
EXPOSE 8099

CMD ["/run.sh"]
