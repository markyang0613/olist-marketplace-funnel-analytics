SELECT 
    s.seller_id,
    COUNT(DISTINCT oi.order_id) AS total_orders,
    ROUND(SUM(oi.price), 2) AS total_sales,
    ROUND(AVG(oi.price), 2) AS avg_item_price,
    ROUND(AVG(r.review_score), 2) AS avg_review_score
FROM sellers s
JOIN order_items oi ON s.seller_id = oi.seller_id
LEFT JOIN order_reviews r ON oi.order_id = r.order_id
GROUP BY 1
HAVING total_orders > 50  -- Focus on established sellers
ORDER BY total_sales DESC
LIMIT 10;