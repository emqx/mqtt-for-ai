# **Enhance MQTT 5.0 with Batch Publishing**

## **1\. Introduction**

### **1.1 Purpose**

This proposal outlines a design for sending multiple logical application messages (sub-messages) within the payload of a single MQTT 5.0 PUBLISH packet. The design leverages MQTT 5.0 User Properties to signal the batch format and size, aiming to improve throughput and efficiency compared to sending numerous small, individual messages.

### **1.2 Motivation**

Transmitting many small, individual messages via MQTT can lead to:
- Increased network overhead due to repeated transmission of packet headers and topic names.
- Higher CPU utilization for packet processing and message routing.
- Reduced throughput and efficiency compared to sending larger payloads.
- Increased the latency due to multiple round trips.

This batching mechanism addresses these issues by consolidating messages destined for the same topic and sharing the same PUBLISH packet attributes (QoS, Retain flag, etc.) into one MQTT transmission, while remaining compliant with the MQTT 5.0 standard.

## **2\. Design**

### **2.1 Packet Structure**

The batch is contained within the payload of a standard MQTT 5.0 PUBLISH packet. Specific User Properties signal the batch nature, format and size.

```
MQTT 5.0 Batch PUBLISH Packet
├── Fixed Header (Type=PUBLISH, QoS, DUP, RETAIN flags)  
├── Remaining Length (Variable Byte Integer)  
├── Variable Header  
│   ├── Topic Name (UTF-8 string)  
│   ├── Packet Identifier (2 bytes, present only if QoS \> 0\)  
│   └── Properties  
│       ├── User Property: "batch-format" \= "v1"  \[2\]  
│       ├── User Property: "batch-size" \= "N"   \[2\]  
│       └──... (Other standard MQTT 5.0 properties like Message Expiry, Content-Type, etc.)  
└── Payload (Batch Payload)  
    ├── Length1 (Variable Byte Integer) \[2, 3\]  
    ├── SubPayload1 (variable bytes)  
    ├── Length2 (Variable Byte Integer) \[2, 3\]  
    ├── SubPayload2 (variable bytes)  
    └──... (Up to N sub-messages)
```

### **2.2 Property Definitions**

* **batch-format (User Property):** MUST be present. A UTF-8 string identifying the version of this batch payload specification (e.g., "v1"). Subscribers use this to select the correct parsing logic.
* **batch-size (User Property):** MUST be present. A UTF-8 string representing a positive integer (N) indicating the exact number of logical sub-messages contained within the Batch Payload.

### **2.3 Payload Format (Batch Payload)**

The Batch Payload consists of N concatenated sub-messages, where N is the integer value specified by the batch-size User Property. Each sub-message MUST be structured as:

* **Length:** A Variable Byte Integer (VBI) as defined in the MQTT 5.0 specification, indicating the number of bytes in the subsequent SubPayload. The VBI encoding allows lengths from 0 up to 256MB using 1 to 4 bytes for the length prefix. 
* **SubPayload:** The actual application data bytes for the logical sub-message. The format of this data is application-specific. Zero-length SubPayloads (Length \= 0\) MAY be permitted based on application policy.

### **2.4 Example (Conceptual)**

For a batch containing two sub-messages, "Msg1" (4 bytes) and "LongerMsg2" (10 bytes):  
Properties:  
User Property: `batch-format \= v1`
User Property: `batch-size \= 2`
Payload:  
`0x04 Msg1 0x0A LongerMsg2`
(Note: 0x04 and 0x0A represent the single-byte VBI encoding for lengths 4 and 10 respectively)

## **3\. Implementation Requirements**

### **3.1 Publisher Requirements**

* MUST set the batch-format User Property to a supported version string (e.g., "v1").  
* MUST set the batch-size User Property to the correct positive integer count of sub-messages in the batch, encoded as a UTF-8 string.  
* MUST format the Batch Payload according to Section 2.3, using VBI for length prefixes.
* MUST ensure the total size of the generated MQTT PUBLISH packet (including headers, properties, and Batch Payload) does not exceed the Maximum Packet Size limit communicated by the broker in the CONNACK packet, if any.
* SHOULD implement and respect configurable upper limits for batch-size and the total byte size of the Batch Payload (see Section 3.3).  
* SHOULD validate sub-payload sizes before sending.

### **3.2 Subscriber Requirements**

* MUST check for the presence and value of the batch-format User Property to ensure compatibility.  
* MUST check for the presence of the batch-size User Property and parse its integer value.  
* MUST parse the Batch Payload according to Section 2.3, correctly decoding VBI lengths.
* MUST perform rigorous validation checks as defined in Section 4 (Error Handling) and Section 7 (Security Considerations).  
* MUST handle malformed batches according to the error handling strategies defined in Section 4\.  
* SHOULD implement and respect configurable upper limits for batch-size and the total byte size of the Batch Payload (see Section 3.3).

### **3.3 Operational Limits**

* Both Publishers and Subscribers SHOULD implement configurable upper limits to prevent resource exhaustion. Recommended defaults:  
  * max-batch-size (sub-message count): 100
  * max-total-batch-payload-size (bytes): 65536
* Implementers MUST adjust these limits based on system constraints, network conditions (e.g., MTU 9), and broker capabilities.  
* Subscribers MUST reject batches exceeding their configured limits (log appropriate error, e.g., BATCH\_SIZE\_LIMIT\_EXCEEDED).

## **4\. Error Handling (Subscriber)**

Subscribers MUST handle malformed batches robustly to ensure stability and prevent crashes or incorrect processing.

### **4.1 Malformed Batch Scenarios**

Subscribers MUST detect the following error conditions during parsing:

1. **Missing/Invalid Properties:** batch-format or batch-size User Property missing, or batch-size is not a positive integer string.  
2. **Unsupported Format:** batch-format value indicates a version not supported by the subscriber.
3. **Invalid VBI Length:** VBI sequence for a sub-payload length is malformed (e.g., \> 4 bytes) or decodes to an invalid value (e.g., negative, or zero if disallowed by policy).
4. **Length Exceeds Payload Boundary:** A decoded VBI length value is greater than the number of bytes remaining in the Batch Payload buffer.
5. **Incomplete Payload Data:** The Batch Payload ends prematurely while reading a VBI length or its corresponding sub-payload data.  
6. **Count Mismatch:** The number of sub-messages successfully parsed does not match the value specified in batch-size (either fewer messages found, or trailing data exists after the Nth message).

### **4.2 Handling Strategies**

* **Mandatory Discard:** For errors 1, 2, 3, 4, or 5, the subscriber MUST discard the entire Batch Payload and MUST NOT process any sub-messages. An error MUST be logged detailing the topic, properties, and a specific reason code (e.g., MALFORMED\_BATCH\_MISSING\_PROPERTY, MALFORMED\_BATCH\_INVALID\_LENGTH, MALFORMED\_BATCH\_INCOMPLETE\_PAYLOAD).  
* **Configurable Count Mismatch (Error 6):**  
  * **Default:** Discard the entire batch and log an error (e.g., MALFORMED\_BATCH\_COUNT\_MISMATCH).  
  * **Optional Partial Processing:** Allow configuration to process the valid sub-messages parsed *before* the mismatch was detected. If enabled and used, MUST log a warning indicating partial processing, messages processed vs. expected count, and the reason (fewer found / trailing data).  
* **Logging:** Error/warning logs MUST include sufficient context (topic, client ID if available, batch properties) and specific error indicators.

## **5\. Interaction with MQTT 5.0 Features**

Core MQTT 5.0 features apply to the PUBLISH packet containing the batch as a single unit.

* **Retain Flag (RETAIN=1):** If set, the broker MUST store the *entire* PUBLISH packet (with the full Batch Payload and all properties) as the single retained message for the topic, replacing any previous one. New subscribers receive this full batch message. Clearing requires publishing a zero-byte payload with RETAIN=1.
* **QoS Levels (0, 1, 2):** The QoS level applies to the delivery assurance of the *entire batch packet* between network hops.
  * QoS 1 (PUBACK) and QoS 2 (PUBREC/PUBREL/PUBCOMP) acknowledgments confirm delivery of the *batch packet*, identified by its Packet Identifier.
  * **Crucially, MQTT QoS does NOT provide application-level atomicity for the sub-messages within the batch.** A subscriber might acknowledge receipt (PUBACK/PUBREC) but fail during subsequent parsing/processing of the Batch Payload. Applications requiring all-or-nothing processing of sub-messages MUST implement their own end-to-end acknowledgment mechanism.  
* **Message Expiry Interval:** If set in the PUBLISH properties, the interval applies to the *entire Application Message* (the batch).2 The broker MUST discard the message for undelivered subscribers if the interval expires before delivery starts. The interval is reduced by the time spent waiting on the broker when forwarded.

## **6\. Comparison with Alternatives**

While this specification uses User Properties and a custom binary format, alternatives exist:

* **JSON Array Payload:** Uses Payload Format Indicator=1, Content Type=application/json. Human-readable, uses standard libraries, but higher overhead and parsing cost.
* **Protobuf/MessagePack Payload:** Uses Payload Format Indicator=0, appropriate Content Type. More efficient binary formats, faster parsing than JSON, but require specific libraries/schemas (Protobuf) and are not human-readable.

The User Property approach is chosen for its flexibility in defining the binary format (allowing potential for minimal overhead), clear signaling of intent via standard MQTT 5.0 properties, and decoupling metadata from the payload. This requires custom parsing logic but offers control over the format.

## **7\. Security Considerations**

Implementing this batching mechanism requires careful attention to security.

* **Authentication & Authorization (Mandatory):**  
  * Clients publishing or subscribing to batch topics MUST be authenticated by the broker (e.g., username/password, client certificates).
  * Brokers MUST use Access Control Lists (ACLs) to enforce that only authorized clients can publish/subscribe to specific batch topics, following the principle of least privilege.
* **Transport Security (Mandatory):**
  * Connections MUST use TLS (typically port 8883\) to encrypt the entire MQTT communication (headers, properties, payload) and protect against eavesdropping and tampering. Client and server certificate validation MUST be performed.
* **Payload Validation (Mandatory):**
  * Subscribers MUST perform rigorous structural validation of the Batch Payload as defined in Section 4 (Error Handling) before attempting to process sub-payloads. Parsers MUST fail safely on error.
  * Applications SHOULD perform content validation on each individual SubPayload based on application-specific logic (e.g., data type, range checks) after successful structural parsing.
* **Denial of Service (DoS) Mitigation (Mandatory):**  
  * Enforce configurable limits on batch-size and max-total-batch-payload-size (Section 3.3) on both publisher and subscriber to prevent resource exhaustion attacks.
  * Brokers SHOULD implement rate limiting (connections/sec, messages/sec per client) to mitigate high-frequency and flooding attacks.
* **Optional Payload Security:**  
  * For end-to-end security where the broker is untrusted, consider encrypting the *entire* Batch Payload at the application level (e.g., AES).
  * Consider signing or using HMAC on the *entire* Batch Payload to ensure integrity and authenticity from the publisher.30 Note: Application-level crypto adds overhead.

## **8\. Future Considerations**

* **Versioning:** New batch formats can be introduced by defining new values for the batch-format User Property (e.g., "v2"). Subscribers would need to support multiple versions.
* **Compression:** To reduce bandwidth, the *entire* Batch Payload MAY be compressed (e.g., using gzip, Zstandard). Compression SHOULD be applied *after* constructing the VBI-prefixed batch payload. The use of compression SHOULD be signaled using the standard MQTT 5.0 Content Type property (e.g., application/vnd.mqtt-batch.v2+gzip) rather than a User Property. 
* **Application-Level Priority:** Priority among sub-messages within a batch is an application-level concern. It would require adding priority information within the SubPayload format and implementing corresponding logic in the subscriber. It is NOT handled by MQTT itself.

## **9\. Conclusion**

This specification provides a framework for batching multiple logical messages within a single MQTT 5.0 PUBLISH packet using User Properties and a VBI-based payload format. By adhering to the implementation requirements, error handling procedures, and security considerations outlined herein, applications can leverage this mechanism to improve efficiency while maintaining protocol compliance and robustness.