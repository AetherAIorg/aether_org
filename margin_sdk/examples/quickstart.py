import margin

margin.configure(api_key="mg_demo_key", base_url="http://localhost:8000")

client = margin.Client()
client.declare(owner="Investment Operations", team="investment-operations")
# client.ingest("../metricgraph/demo/investment_ops_demo")
# client.context.link("Fund-Level Net IRR", uses_table="fund_cashflows_v2")
# client.sync()
# print(client.graph.context("Fund-Level Net IRR"))
