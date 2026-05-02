-- KPI: Average Delivery Time by State
SELECT 
    c.customer_state,
    COUNT(o.order_id) as total_orders,
    ROUND(AVG(date_diff('day', o.order_purchase_timestamp::TIMESTAMP, o.order_delivered_customer_date::TIMESTAMP)), 2) AS avg_delivery_days
FROM orders o
JOIN customers c USING (customer_id)
WHERE o.order_status = 'delivered'
GROUP BY 1
ORDER BY avg_delivery_days DESC;