## Introduction

This specification extends the MQTT 5.0 protocol to support subscription filters, allowing clients to receive only a subset of messages matching a topic filter. Subscription filters allow MQTT brokers to filter messages routed to subscribers, improving flexibility, reducing network traffic, and optimizing resource utilization. This enhancement enables more granular control over message delivery, catering to scenarios where clients require specific subsets of data from a topic.

## Design

The MQTT 5.0 specification allows subscribers to use topic filters only, resulting in the following message routing path:

`Publisher --> Topic -- (Filter) --> Subscription --> Subscriber`

Subscription filters introduce a second level of filtering in the message routing path, providing more fine-grained control:

`Publisher --> Topic -- (Filter) --> Subscription -- (Filter) --> Subscriber`	

This two-level filtering mechanism allows for both topic-based and content-based filtering, enabling clients to precisely specify the messages they wish to receive.

## Syntax

A subscription filter is appended to the topic filter using a question mark (?) as a delimiter. The syntax is as follows:

`<topic-filter>?<filter-expression>`

Where:

- \<topic-filter>: A standard MQTT topic filter (e.g., sensor/+/temperature, home/#).

- ?: Delimiter separating the topic filter and filter expression.

- \<filter-expression>: A string representing the filter criteria.

## Filter Expression

The filter expression is a simple key-value pair based filtering mechanism.

Format: `key=value`

- Multiple filters can be combined using logical AND (`&`). Example: `key1=value1&key2=value2`.

- The key and value are extracted from the message's properties.

- The filter is applied to the JSON object's key-value pairs.

## Behavior

When a client subscribes to a topic with a filter, the server will only deliver messages that match both the topic filter and the filter expression.

- If the specified keys are not found in the message properties, the message is filtered out.

- If the subscription does not contain a `?`, the subscription is treated as a standard MQTT subscription.

- The filter expression is case-sensitive.

## Examples

- `sensor/+/temperature?location=roomA`: Subscribes to temperature readings from any sensor, but only those where the message properties contain {"location": "roomA"}.

- `sensor/+/temperature?value>25`: Subscribes to temperature readings from any sensor, but only those where the message properties contain "value" key, and the value is greater than 25. 

- `home/lights/#`: Standard MQTT subscription, no filtering.

## Implementation Notes

- Servers must parse the subscription string and extract the topic filter and filter expression.

- Servers must implement the filter logic based on the specified expression.

- Clients are not required to do any filtering; the server is responsible.

- Error handling for malformed filter expressions is server-specific.

## Future Considerations

- Support for more complex filter expressions (e.g., numerical comparisons, regular expressions).

- Support for filters on MQTT payload.

