-- 100,000 products across the seeded categories, in one statement (about a second).
-- Run after `alembic upgrade head` and `python -m app.seed --products 0` (which creates categories).
INSERT INTO products (category_id, sku, name, slug, description, brand, price, mrp, stock, weight_grams, attributes, is_active)
SELECT c.id,
       'BEN-' || lpad(g::text, 7, '0'),
       b.brand || ' ' || m.word || ' ' || c.name,
       'bench-' || g,
       'Benchmark product ' || g,
       b.brand,
       p.price,
       (p.price * (1 + (g % 4) * 0.1))::int,
       CASE WHEN g % 10 = 0 THEN 0 ELSE (g % 200) END,
       200 + (g % 1800),
       jsonb_build_object(
           'color', (ARRAY['black', 'white', 'red', 'blue', 'green', 'grey'])[1 + g % 6],
           'size', (ARRAY['S', 'M', 'L', 'XL'])[1 + g % 4]
       ),
       g % 50 <> 0
FROM generate_series(1, 100000) g
CROSS JOIN LATERAL (SELECT ((199 + (g * 7919) % 9800) * 100) AS price) p
CROSS JOIN LATERAL (SELECT (ARRAY['Nike', 'Adidas', 'Puma', 'Reebok', 'Bata', 'Woodland', 'Campus', 'Sparx'])[1 + g % 8] AS brand) b
CROSS JOIN LATERAL (SELECT (ARRAY['Air', 'Flex', 'Street', 'Urban', 'Trail', 'Classic', 'Swift', 'Cloud'])[1 + (g / 8) % 8] AS word) m
JOIN LATERAL (SELECT id, name FROM categories ORDER BY id OFFSET (g % 16) LIMIT 1) c ON true;

ANALYZE products;
