| table_name            | column_name            | data_type                | is_nullable |
| --------------------- | ---------------------- | ------------------------ | ----------- |
| merchants             | id                     | bigint                   | NO          |
| merchants             | merchant_code          | text                     | NO          |
| merchants             | merchant_name          | text                     | NO          |
| merchants             | created_at             | timestamp with time zone | YES         |
| merchants             | merchant_id_code       | text                     | YES         |
| profiles              | id                     | uuid                     | NO          |
| profiles              | username               | text                     | NO          |
| profiles              | created_at             | timestamp with time zone | YES         |
| profiles              | role                   | text                     | YES         |
| profiles              | notes                  | text                     | YES         |
| profiles              | permissions            | jsonb                    | YES         |
| shipping_costs        | id                     | uuid                     | NO          |
| shipping_costs        | created_at             | timestamp with time zone | NO          |
| shipping_costs        | date                   | date                     | YES         |
| shipping_costs        | freight_unit_price     | numeric                  | YES         |
| shipping_costs        | total_settle_weight    | numeric                  | YES         |
| shipping_costs        | actual_weight_with_box | numeric                  | YES         |
| shipping_costs        | tracking_number        | text                     | YES         |
| shipping_costs        | shipment_id            | text                     | YES         |
| shipping_costs        | merchants              | jsonb                    | YES         |
| shipping_costs        | order_number           | text                     | YES         |
| temu_shipment_details | id                     | bigint                   | NO          |
| temu_shipment_details | workflow_id            | bigint                   | NO          |
| temu_shipment_details | merchant               | text                     | NO          |
| temu_shipment_details | quantity               | integer                  | NO          |
| temu_shipment_details | scan_channel           | text                     | YES         |
| temu_shipment_details | notes                  | text                     | YES         |
| temu_shipment_details | created_at             | timestamp with time zone | YES         |
| temu_shipment_ids     | id                     | bigint                   | NO          |
| temu_shipment_ids     | workflow_id            | bigint                   | NO          |
| temu_shipment_ids     | shipment_id_value      | text                     | NO          |
| temu_shipment_ids     | created_at             | timestamp with time zone | YES         |
| temu_workflow         | id                     | bigint                   | NO          |
| temu_workflow         | cn_send_date           | date                     | YES         |
| temu_workflow         | main_tracking_id       | text                     | YES         |
| temu_workflow         | box_code               | text                     | YES         |
| temu_workflow         | box_count              | integer                  | YES         |
| temu_workflow         | inner_count            | integer                  | YES         |
| temu_workflow         | status                 | text                     | YES         |
| temu_workflow         | us_receive_date        | date                     | YES         |
| temu_workflow         | us_box_count           | integer                  | YES         |
| temu_workflow         | us_actual_count        | integer                  | YES         |