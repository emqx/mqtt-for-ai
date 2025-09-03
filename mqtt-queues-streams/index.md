## Introduction

This spec enhances the standard MQTT 5.0 protocol with native support for queues and streams while maintaining compatibility with the MQTT 5.0 specification.

The key idea is to use specially formatted topic names to indicate queue and stream subscriptions, and to leverage MQTT 5.0's User Properties for configuring queue/stream behavior.

## Motivation

While MQTT 5.0 offers robust publish/subscribe functionality, it lacks built-in support for queueing and streaming semantics. These are often implemented at the application level, leading to inconsistencies and increased complexity. This spec seeks to address this by providing standardized mechanisms for:

- Queueing: 

  Provides traditional first-in-first-out (FIFO) and store-and-forward queues.

- Streaming: 

  Implements data streaming functionality similar to Apache Kafka and AWS Kinesis.

## MQTT Queue Subscription

### Syntax

Queue subscriptions are identified by a specific topic name format:

`$queue/{queue_name}/{topic_filter}`

Where:

`$queue` is a reserved prefix indicating a queue subscription.

`{queue_name}` is a unique identifier for the queue within the broker.

`{topic_filter}` is a standard MQTT topic filter, specifying the messages that will be routed to the queue.

### Queue Semantics

- Messages matching the `{topic_filter}` are added to the queue.

- Consumers subscribe to the queue (using the `$queue/...` syntax) to receive messages.

- Messages are typically delivered to only one consumer (e.g., using a first-in, first-out delivery mechanism). This is similar to how shared subscriptions work, but the key difference is that with queues, the broker also manages message retention.

- The broker is responsible for persisting messages in the queue, according to the configured retention policy.

- If no consumers are online, messages are retained in the queue until a consumer becomes available or the retention policy expires.

### Queue Properties

Queue properties are specified using MQTT 5.0 User Properties within the SUBSCRIBE packet. The following properties are defined:

- `size (integer)`: Maximum number of messages the queue can hold. If this limit is reached, the broker's behavior (e.g., rejecting new messages, discarding oldest messages) is implementation-specific, but the behavior SHOULD be documented.

- `retention (string)`: Duration for which messages are retained in the queue. The format SHOULD follow the ISO 8601 duration format (e.g., "PT1H", "P1D", "PT2H30M"). If not provided, the broker SHOULD use a default retention policy. 

- `deliveryMode (string, optional)`: "exclusive" or "shared".

  "exclusive": Only one consumer can subscribe to the queue at a time. Subsequent subscriptions are rejected. This is the default.

  "shared": Multiple consumers can subscribe to the queue. Messages are distributed among consumers (similar to shared subscriptions).

- description (string): Human-readable description of the queue.

### Examples

Assume messages are published to the topic `sensors/temperature/rooms/1`.

- `$queue/sensors-data/sensors/#`: A queue named "sensors-data" that receives all sensor data.

  User Properties: size=1000, retention=PT1H, description=Temperature and humidity readings.

- `$queue/rooms-data/sensors/+/rooms/+`: A queue named "rooms-data" that receives data for specific rooms.

  User Properties: size=500, retention=P1D, deliveryMode=shared.

- `$queue/temperature-data/sensors/temperature/#`: A queue named "temperature-data" that receives only temperature data.

  User Properties: retention=PT12H.

- `$queue/room1-temperature/sensors/temperature/rooms/1`: A queue named "room1-temperature" that receives temperature data only for room 1.

## MQTT Stream Subscription

### Syntax

Stream subscriptions use the following topic name format:

`$stream/{stream_name}/{topic_filter}`

Where:

- `$stream` is a reserved prefix indicating a stream subscription.

- `{stream_name}` is a unique identifier for the stream.

- `{topic_filter}` is a standard MQTT topic filter, specifying the messages that are included in the stream.

### Stream Semantics

- Messages matching the `{topic_filter}` are appended to the stream.

- Consumers subscribe to the stream (using the `$stream/...` syntax) to receive messages.

- Messages are delivered to consumers in the order they are added to the stream.

- The broker persists messages in the stream, according to the configured retention policy.

- Consumers can specify an offset to start consuming from a specific point in the stream, enabling replay functionality.

- Multiple consumers can read from the same stream, each with its own offset.

### Stream Properties

Stream properties are specified using MQTT 5.0 User Properties in the SUBSCRIBE packet:

- retention (string): Duration for which messages are retained in the stream. The format SHOULD follow the ISO 8601 duration format (e.g., "PT1H", "P1D", "PT2H30M"). If not provided, the broker SHOULD use a default retention policy.

- partitions (integer, optional): Number of partitions in the stream. Partitions allow for parallel processing of the stream. If not specified, the broker SHOULD use a default number of partitions (e.g., 0). Partitioning details (how messages are assigned to partitions) are broker-specific.

- offset (string, optional): The starting offset for the consumer. Valid values are:

  "earliest": Start consuming from the beginning of the stream.

  "latest": Start consuming from the most recently added message.

  A numeric value: The absolute offset.

  If not provided, the broker SHOULD use the "latest" offset.

- description (string): Human-readable description of the stream.

### Examples

Assume messages are published to the topic sensors/temperature/rooms/1.

- `$stream/sensors-data/sensors/#`: A stream named "sensors-data" containing all sensor data.

  User Properties: retention=P1D, partitions=3, description=Aggregated sensor readings.

- `$stream/rooms-data/sensors/+/rooms/+`: A stream named "rooms-data" containing data for specific rooms.

  User Properties: retention=P7D, offset=earliest.

- `$stream/temperature-data/sensors/temperature/#`: A stream named "temperature-data" containing only temperature data.

  User Properties: retention=PT12H, offset=1000.

- `$stream/room1-temperature/sensors/temperature/rooms/1`: A stream named "room1-temperature" containing temperature data only for room 1.

## MQTT Shared Subscription

### Syntax

Shared subscriptions follow the MQTT 5.0 specification:

`$share/{group_name}/{topic_filter}`

Where:

- `$share` is the prefix indicating a shared subscription.

- `{group_name}` is the name of the shared subscription group.

- `{topic_filter}` is the MQTT topic filter.

### Shared Subscription Semantics

- MQTT 5.0 Shared subscriptions allow multiple clients to subscribe to the same topic filter, with the broker distributing messages among the subscribers in the group.

- This provides load balancing and scalability for message consumption.

### Examples

For messages published to `sensors/temperature/rooms/1`:

- `$share/sensors-group/sensors/#`: Messages are shared among clients in the "sensors-group".

- `$share/temperature-group/+/temperature/#`: Messages are shared among clients in the "temperature-group" for all temperature topics.

## Broker Behavior

### Queue and Stream Declaration

- The broker creates a queue or stream when it receives a SUBSCRIBE packet with a topic name matching the $queue/... or $stream/... syntax.

- If a queue or stream with the given name already exists, the broker SHOULD validate that the properties in the new SUBSCRIBE packet are compatible with the existing configuration. If there are conflicts, the broker SHOULD return a SUBACK with an appropriate reason code.

### Message Routing

When a PUBLISH message is received, the broker routes the message to any matching queue and stream subscriptions, in addition to regular MQTT subscriptions.

- For queue subscriptions, the broker adds the message to the queue according to the queue's size and retention properties.

- For stream subscriptions, the broker adds the message to the stream, handling partitioning if configured.

### Message Delivery

- For queue subscriptions, the broker delivers messages from the queue to the consumers. The delivery mechanism (e.g., FIFO, round-robin) is broker-specific, but SHOULD be documented.

- For stream subscriptions, the broker delivers messages from the stream to the consumers, starting from their specified offset. The broker MUST maintain the order of messages within a partition.

### Error Handling

- The broker SHOULD use MQTT 5.0 reason codes in SUBACK and PUBACK packets to indicate success or failure of queue/stream operations.

- If a queue or stream cannot be created or a subscription fails, the broker SHOULD return a SUBACK with a specific reason code (e.g., "Queue Full", "Invalid Offset").

- If a PUBLISH message cannot be added to a queue (e.g., due to size limits), the broker's behavior is implementation-specific (e.g., sending a PUBACK with a failure reason code, discarding the message). This behavior SHOULD be documented.

## Client Behavior

### Subscribing to Queues and Streams

- Clients subscribe to queues and streams using the `$queue/...` and `$stream/...` topic name formats in the SUBSCRIBE packet.

- Clients use MQTT 5.0 User Properties in the SUBSCRIBE packet to specify queue/stream properties.

### Consuming Messages

Clients receive messages from queues and streams as regular PUBLISH messages.

For streams, clients are responsible for managing their offset if they need to consume messages from a specific point or replay messages. The client can close the subscription and re-subscribe with a different offset.

## Future Considerations

- Queue/Stream Management API: Standardize a management API for creating, deleting, and configuring queues and streams, potentially using HTTP or MQTT control topics. 

- Message Batch: Add support for batching related messages within streams, ensuring they are delivered together to consumers.

- Transaction Support: Investigate adding transactional capabilities for message publishing and consumption, ensuring atomicity.

