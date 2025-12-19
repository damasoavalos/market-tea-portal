from .engine import ReportConfig

CFG_RESTOCKING_REPORT = ReportConfig(
    excel_column_map={
        'Product SKU': 'tea_id',
        'Product name': 'tea_name',
        'Option 1': 'weight_g',
        'Total Quantity Sold': 'quantity_sold',
    },
    db_sql="""
        select
            tp.id              as tea_id,
            tp.market_category as category, 
            tp.jar_capacity_g,
            v.package_type,
            v.package_grams
        from inventory.tea_products tp
        join vendors.v_all_vendors v
          on tp.id = v.market_tea_id
    """,
    output_excel_name="product_sales_report"
)


