import pathlib
import pandas as pd
import numpy as np

out_dir = pathlib.Path("docs/step0")
out_dir.mkdir(parents=True, exist_ok=True)

for slug, z_name in [("pathanamthitta_kozhencherry", "Pathanamthitta"), ("kottayam_pala", "Kottayam")]:
    csv_path = out_dir / f"alerts_2026_{slug}.csv"
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    
    # Filter alert days (warning or danger)
    alerts = df[df["alert_level"] != "NORMAL"].sort_values("date").reset_index(drop=True)
    
    # Group into contiguous blocks
    blocks = []
    if len(alerts) > 0:
        cur_block = [alerts.iloc[0]]
        for i in range(1, len(alerts)):
            prev_d = alerts.iloc[i-1]["date"]
            cur_d = alerts.iloc[i]["date"]
            if (cur_d - prev_d).days == 1:
                cur_block.append(alerts.iloc[i])
            else:
                blocks.append(pd.DataFrame(cur_block))
                cur_block = [alerts.iloc[i]]
        blocks.append(pd.DataFrame(cur_block))
        
    print(f"\n{'='*80}\n2026 ALERT BLOCKS: {z_name} ({slug})\n{'='*80}")
    out_lines = []
    out_lines.append(f"# 2026 Alert Blocks: {z_name}\n")
    
    for b_idx, b_df in enumerate(blocks, 1):
        st = b_df["date"].min().strftime("%Y-%m-%d")
        en = b_df["date"].max().strftime("%Y-%m-%d")
        hdr = f"Block {b_idx}: {st} to {en} ({len(b_df)} days)"
        print(f"\n--- {hdr} ---")
        out_lines.append(f"### {hdr}\n")
        
        cols_show = ["date", "alert_level", "risk_score", "rain_1d", "rain_3d", "rain_7d", "soil_0_7_t1", "soil_7_28_t1"]
        b_show = b_df[cols_show].copy()
        b_show["date"] = b_show["date"].dt.strftime("%Y-%m-%d")
        s_table = b_show.to_string(index=False)
        print(s_table)
        out_lines.append("```\n" + s_table + "\n```\n")
        
    (out_dir / f"alert_blocks_2026_{slug}.md").write_text("\n".join(out_lines), encoding="utf-8")

print("\n2026 alert blocks saved to docs/step0/.")
