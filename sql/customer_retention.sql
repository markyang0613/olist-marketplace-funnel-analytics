-- KPI: Repeat Purchase Rate (Retention)
WITH customer_orders AS (
    SELECT 
        customer_unique_id,
        COUNT(order_id) as order_count
    FROM orders
    JOIN customers USING (customer_id)
    GROUP BY 1
)
SELECT 
    CASE WHEN order_count > 1 THEN 'Repeat Customer' ELSE 'One-Time Customer' END AS customer_type,
    COUNT(*) AS total_customers,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM customer_orders), 2) AS pct_of_base
FROM customer_orders
GROUP BY 1;