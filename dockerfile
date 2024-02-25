FROM alpine

# Install SQLite
RUN apk add --no-cache sqlite python3 py3-pip

# Create the data directory
RUN mkdir /data

# Start SQLite with an empty database
CMD ["sqlite3" "/data/mydatabase.db"]
