import pandas as pd
df = pd.read_csv("outputs/flow_stats.csv")
# Save throughput per flow
df.to_csv("outputs/real_throughput_by_flow.csv", index=False)

# Aggregate per destination (proxy for overall downlink throughput)
agg = df.groupby("dstAddr").agg({"throughput_bps":["mean","sum"], "rxBytes":"sum"}).reset_index()
agg.columns = ["dstAddr","throughput_mean_bps","throughput_sum_bps","rxBytes_sum"]
agg.to_csv("outputs/real_throughput_summary.csv", index=False)

print("Wrote outputs/real_throughput_summary.csv and outputs/real_throughput_by_flow.csv")
