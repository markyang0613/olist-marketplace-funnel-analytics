SELECT 
    date_trunc('month', order_purchase_timestamp::TIMESTAMP) AS months,
    ROUND(SUM(price), 2) AS gmv,
    COUNT(DISTINCT order_id) AS total_orders
FROM orders
JOIN order_items USING (order_id)
WHERE order_status = 'delivered'
GROUP BY 1
ORDER BY 1 DESC;
