-- Measuring the Fulfillment Funnel (in Days)
SELECT 
    order_status,
    -- 1. Approval Lag: Time for payment to be approved
    AVG(date_diff('hour', order_purchase_timestamp::TIMESTAMP, order_approved_at::TIMESTAMP) / 24.0) AS avg_approval_days,
    -- 2. Processing Lag: Time for seller to hand over to carrier
    AVG(date_diff('hour', order_approved_at::TIMESTAMP, order_delivered_carrier_date::TIMESTAMP) / 24.0) AS avg_seller_dispatch_days,
    -- 3. Delivery Lag: Carrier to Customer
    AVG(date_diff('hour', order_delivered_carrier_date::TIMESTAMP, order_delivered_customer_date::TIMESTAMP) / 24.0) AS avg_carrier_delivery_days,
    -- 4. Total Lead Time
    AVG(date_diff('hour', order_purchase_timestamp::TIMESTAMP, order_delivered_customer_date::TIMESTAMP) / 24.0) AS total_lead_time_days
FROM orders
WHERE order_status = 'delivered'
GROUP BY 1;