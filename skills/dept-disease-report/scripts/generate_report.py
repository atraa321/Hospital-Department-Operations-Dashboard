from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from xml.sax.saxutils import escape

from sqlalchemy import create_engine, text


def read_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        row = line.strip()
        if not row or row.startswith("#") or "=" not in row:
            continue
        k, v = row.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def normalize_db_url(url: str) -> str:
    if url.startswith("mysql+mysqlconnector://"):
        url = url.replace("mysql+mysqlconnector://", "mysql+pymysql://", 1)
    p = urlparse(url)
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() != "use_pure"]
    return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(q), p.fragment))


def resolve_db_url(project_root: Path, arg_db_url: str | None) -> str:
    if arg_db_url:
        return normalize_db_url(arg_db_url)
    env = read_env(project_root / "backend" / ".env")
    raw = env.get("DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw:
        raise ValueError("DATABASE_URL is missing. Pass --db-url or configure backend/.env")
    return normalize_db_url(raw)


def one(conn, sql: str, params: dict) -> dict:
    return dict(conn.execute(text(sql), params).mappings().one())


def all_rows(conn, sql: str, params: dict) -> list[dict]:
    return [dict(r) for r in conn.execute(text(sql), params).mappings().all()]


def f2(v: float | int | None) -> str:
    return f"{float(v or 0):.2f}"


def pct(v: float) -> str:
    return f"{v:.2f}%"


def pct_change(curr: float | int, base: float | int) -> str:
    b = float(base or 0)
    c = float(curr or 0)
    if b == 0:
        return "N/A"
    return f"{((c - b) / b * 100):+.2f}%"


def shift_year(d: date, years: int) -> date:
    y = d.year + years
    while True:
        try:
            return d.replace(year=y)
        except ValueError:
            d = d - timedelta(days=1)


def month_start(d: date) -> date:
    return d.replace(day=1)


def add_months(d: date, months: int) -> date:
    total = (d.year * 12 + (d.month - 1)) + months
    y = total // 12
    m = total % 12 + 1
    return date(y, m, 1)


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    out.extend("| " + " | ".join(r) + " |" for r in rows)
    return "\n".join(out)


def safe_name(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]+', "_", name.strip())
    name = re.sub(r"\s+", "_", name)
    return name or "report"


RULE_CODE_ZH = {
    "R_COST": "次均费用异常",
    "R_LOS": "住院日异常",
    "R_DRUG_RATIO": "非草药药占比异常",
    "R_AUX_CHECK": "辅助检查占比异常",
}

SEVERITY_ZH = {
    "YELLOW": "轻度预警",
    "ORANGE": "中度预警",
    "RED": "重度预警",
}

MAPPING_STATUS_ZH = {
    "MAPPED": "已映射",
    "UNMAPPED": "未映射",
    "MANUAL": "人工维护",
    "(无映射记录)": "无映射记录",
}


def label_rule_code(code: str) -> str:
    zh = RULE_CODE_ZH.get(code)
    return f"{code}（{zh}）" if zh else code


def label_severity(level: str) -> str:
    zh = SEVERITY_ZH.get(level)
    return f"{level}（{zh}）" if zh else level


def label_mapping_status(status: str) -> str:
    zh = MAPPING_STATUS_ZH.get(status)
    return f"{status}（{zh}）" if zh else status


def short_text(text: str, max_len: int = 24) -> str:
    s = (text or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def resolve_matplotlib_font_name() -> str | None:
    try:
        import matplotlib.font_manager as fm
    except Exception:
        return None

    preferred = [
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
    ]
    installed = {f.name for f in fm.fontManager.ttflist}
    for name in preferred:
        if name in installed:
            return name

    for p in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\simsun.ttc"]:
        if Path(p).exists():
            try:
                return fm.FontProperties(fname=p).get_name()
            except Exception:
                continue
    return None


def generate_charts(data: dict, output_dir: Path, base_name: str) -> list[dict[str, str]]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.ticker import FuncFormatter
    except Exception as exc:
        print(f"[WARN] skip charts: matplotlib unavailable ({exc})")
        return []

    font_name = resolve_matplotlib_font_name()
    if font_name:
        plt.rcParams["font.sans-serif"] = [font_name]
    plt.rcParams["axes.unicode_minus"] = False

    chart_dir = output_dir / f"{base_name}_charts"
    chart_dir.mkdir(parents=True, exist_ok=True)
    charts: list[dict[str, str]] = []

    def save_chart(fig, filename: str, title: str, caption: str) -> None:
        fig.tight_layout()
        chart_path = chart_dir / filename
        fig.savefig(chart_path, dpi=160, bbox_inches="tight")
        plt.close(fig)
        charts.append(
            {
                "title": title,
                "caption": caption,
                "path": str(chart_path),
                "md_path": f"{chart_dir.name}/{filename}".replace("\\", "/"),
            }
        )

    monthly = data.get("monthly") or []
    if monthly:
        months = [str(r["month"]) for r in monthly]
        case_counts = [int(r["case_count"] or 0) for r in monthly]
        avg_costs = [float(r["avg_cost"] or 0) for r in monthly]
        fig, ax1 = plt.subplots(figsize=(10, 4.2))
        ax1.bar(months, case_counts, color="#5B8FF9", label="病例数")
        ax1.set_xlabel("月份")
        ax1.set_ylabel("病例数（例）")
        ax1.tick_params(axis="x", rotation=30)

        ax2 = ax1.twinx()
        ax2.plot(months, avg_costs, color="#F6BD16", marker="o", linewidth=2, label="次均费用")
        ax2.set_ylabel("次均费用（元）")
        ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))

        l1, t1 = ax1.get_legend_handles_labels()
        l2, t2 = ax2.get_legend_handles_labels()
        ax1.legend(l1 + l2, t1 + t2, loc="upper left")
        ax1.set_title("月度病例量与次均费用趋势")
        save_chart(fig, "monthly_cases_avg_cost.png", "月度病例量与次均费用趋势", "用于观察就诊规模与费用水平的同步波动。")

    disease_top = (data.get("disease_top_cost") or [])[:10]
    if disease_top:
        labels = [short_text(f"{r['diag_code']} {r['diag_name']}") for r in disease_top][::-1]
        values = [float(r["total_cost"] or 0) for r in disease_top][::-1]
        fig, ax = plt.subplots(figsize=(10, 5.2))
        ax.barh(labels, values, color="#5AD8A6")
        ax.set_xlabel("总费用（元）")
        ax.set_title("重点病种费用贡献TOP10")
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:,.0f}"))
        save_chart(fig, "disease_top10_total_cost.png", "重点病种费用贡献TOP10", "用于识别费用贡献高、应优先管理的病种。")

    dip_status = data.get("dip_status") or []
    if dip_status:
        labels = [label_mapping_status(str(r["status"])) for r in dip_status]
        values = [int(r["cnt"] or 0) for r in dip_status]
        fig, ax = plt.subplots(figsize=(8.2, 4.2))
        colors = ["#5B8FF9", "#F6BD16", "#E8684A", "#6DC8EC", "#9270CA"]
        ax.bar(labels, values, color=colors[: len(values)])
        for i, v in enumerate(values):
            ax.text(i, v, str(v), ha="center", va="bottom", fontsize=9)
        ax.set_ylabel("病例数（例）")
        ax.set_title("DIP映射状态分布")
        ax.tick_params(axis="x", rotation=15)
        save_chart(fig, "dip_mapping_status.png", "DIP映射状态分布", "用于评估DIP入组覆盖和异常状态构成。")

    unmapped_reason = (data.get("dip_unmapped_reason") or [])[:10]
    if unmapped_reason:
        labels = [short_text(str(r["fail_reason"])) for r in unmapped_reason][::-1]
        values = [int(r["cnt"] or 0) for r in unmapped_reason][::-1]
        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.barh(labels, values, color="#E8684A")
        ax.set_xlabel("病例数（例）")
        ax.set_title("UNMAPPED原因分布TOP10")
        save_chart(fig, "dip_unmapped_reason_top10.png", "UNMAPPED原因分布TOP10", "用于定位编码与映射规则的主要异常来源。")

    compare = data.get("compare")
    if compare:
        metric_labels = ["病例数", "总费用", "次均费用", "平均住院日", "平均药占比"]
        yoy_values = [
            compare["case_count"]["yoy_pct"],
            compare["total_cost"]["yoy_pct"],
            compare["avg_cost"]["yoy_pct"],
            compare["avg_los"]["yoy_pct"],
            compare["avg_drug_ratio"]["yoy_pct"],
        ]
        mom_values = [
            compare["case_count"]["mom_pct"],
            compare["total_cost"]["mom_pct"],
            compare["avg_cost"]["mom_pct"],
            compare["avg_los"]["mom_pct"],
            compare["avg_drug_ratio"]["mom_pct"],
        ]
        x = list(range(len(metric_labels)))
        w = 0.35
        fig, ax = plt.subplots(figsize=(10, 4.8))
        y1 = [float(v.replace("%", "")) if v != "N/A" else 0.0 for v in yoy_values]
        y2 = [float(v.replace("%", "")) if v != "N/A" else 0.0 for v in mom_values]
        ax.bar([i - w / 2 for i in x], y1, width=w, color="#5B8FF9", label="同比")
        ax.bar([i + w / 2 for i in x], y2, width=w, color="#F6BD16", label="环比")
        ax.axhline(0, color="#666666", linewidth=0.8)
        ax.set_xticks(x)
        ax.set_xticklabels(metric_labels)
        ax.set_ylabel("变化幅度（%）")
        ax.set_title("核心指标同比/环比变化")
        ax.legend(loc="upper right")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
        save_chart(fig, "kpi_yoy_mom_change.png", "核心指标同比/环比变化", "用于直观比较病例数、费用与效率指标的同比和环比变化方向。")

    return charts


def refresh_dip(engine, project_root: Path) -> dict:
    from sqlalchemy.orm import sessionmaker

    backend = project_root / "backend"
    if str(backend.resolve()) not in sys.path:
        sys.path.insert(0, str(backend.resolve()))
    from app.services.dip_service import recalculate_mappings  # type: ignore

    SessionLocal = sessionmaker(bind=engine, future=True)
    with SessionLocal() as db:
        return recalculate_mappings(db=db, limit=50000)


def build_markdown(data: dict) -> str:
    d = data
    top_disease = d["disease_top_cost"][0] if d["disease_top_cost"] else None
    peak_case_month = max(d["monthly"], key=lambda x: int(x["case_count"] or 0)) if d["monthly"] else None
    peak_cost_month = max(d["monthly"], key=lambda x: float(x["avg_cost"] or 0)) if d["monthly"] else None
    top_cost_group = d["cost_group"][0] if d["cost_group"] else None
    workorder_total = sum(int(r["cnt"] or 0) for r in d["workorders"])
    lines: list[str] = []
    lines.append(f"# {d['year']}年{d['dept']}病种分析报告（数据库版）")
    lines.append("")
    lines.append("## 一、报告说明")
    lines.append("- 数据来源：MySQL `disease_analytics` 数据库。")
    lines.append(f"- 分析对象：{d['dept']}。")
    lines.append(f"- 统计周期：{d['date_from']} 至 {d['date_to']}（按出院日期）。")
    lines.append(f"- 生成时间：{d['generated_at']}。")
    lines.append("- 分析框架：依据《病种分析步骤.md》五步法。")
    lines.append("")
    if d.get("compare"):
        c = d["compare"]
        lines.append("## 二、同比与环比分析")
        lines.append(
            f"- 同比口径：与上年同期（{c['yoy_period'][0]} 至 {c['yoy_period'][1]}）对比。"
        )
        lines.append(
            f"- 环比口径：以本期末月（{c['mom_period'][0]}）与上月（{c['mom_period'][1]}）对比。"
        )
        lines.append(
            md_table(
                ["指标", "本期", "同比基准", "同比变化", "环比基准", "环比变化"],
                [
                    ["病例数(例)", str(c["case_count"]["curr"]), str(c["case_count"]["yoy_base"]), c["case_count"]["yoy_pct"], str(c["case_count"]["mom_base"]), c["case_count"]["mom_pct"]],
                    ["总费用(元)", f2(c["total_cost"]["curr"]), f2(c["total_cost"]["yoy_base"]), c["total_cost"]["yoy_pct"], f2(c["total_cost"]["mom_base"]), c["total_cost"]["mom_pct"]],
                    ["次均费用(元)", f2(c["avg_cost"]["curr"]), f2(c["avg_cost"]["yoy_base"]), c["avg_cost"]["yoy_pct"], f2(c["avg_cost"]["mom_base"]), c["avg_cost"]["mom_pct"]],
                    ["平均住院日(天)", f2(c["avg_los"]["curr"]), f2(c["avg_los"]["yoy_base"]), c["avg_los"]["yoy_pct"], f2(c["avg_los"]["mom_base"]), c["avg_los"]["mom_pct"]],
                    ["平均药占比(%)", f2(c["avg_drug_ratio"]["curr"]), f2(c["avg_drug_ratio"]["yoy_base"]), c["avg_drug_ratio"]["yoy_pct"], f2(c["avg_drug_ratio"]["mom_base"]), c["avg_drug_ratio"]["mom_pct"]],
                ],
            )
        )
        lines.append(
            "小结：同比用于评估年度变化趋势，环比用于观察近期波动。建议对同比和环比同时上升的费用类指标优先开展专项复盘。"
        )
        lines.append("")

    lines.append("## 三、按《病种分析步骤.md》执行结果")
    lines.append("")

    lines.append("### 第1步：定病种（明确管理重点）")
    lines.append(
        f"- 本期病例 **{d['case_count']}** 例，总费用 **{f2(d['total_cost'])}** 元，"
        f"次均费用 **{f2(d['avg_cost'])}** 元，平均住院日 **{f2(d['avg_los'])}** 天。"
    )
    lines.append(
        f"- 全院占比：病例 **{pct(d['case_share'])}**，费用 **{pct(d['cost_share'])}**；药占比 **{pct(d['avg_drug_ratio'])}**。"
    )
    lines.append("- 结合病例量、费用贡献和波动性，建议将以下病种列为重点病种。")
    lines.append("重点病种TOP10（按费用）")
    lines.append(
        md_table(
            ["诊断编码", "诊断名称", "总费用(元)", "费用占比", "病例数", "次均费用(元)", "费用波动CV%"],
            [
                [
                    str(r["diag_code"]),
                    str(r["diag_name"]),
                    f2(r["total_cost"]),
                    pct((float(r["total_cost"] or 0) / d["total_cost"] * 100) if d["total_cost"] else 0),
                    str(int(r["case_count"] or 0)),
                    f2(r["avg_cost"]),
                    f2(r["cv_cost"]),
                ]
                for r in d["disease_top_cost"]
            ],
        )
    )
    if top_disease:
        lines.append(
            f"本步小结：本期病种费用集中度较高，首位病种为 {top_disease['diag_code']} "
            f"{top_disease['diag_name']}，费用占比 {pct((float(top_disease['total_cost'] or 0) / d['total_cost'] * 100) if d['total_cost'] else 0)}。"
            "建议将费用集中病种纳入重点管理清单，按月跟踪。"
        )
    lines.append("")

    lines.append("### 第2步：拆结构（形成病种与费用画像）")
    lines.append("月度趋势")
    lines.append(
        md_table(
            ["月份", "病例数", "总费用(元)", "次均费用(元)", "平均住院日", "平均药占比"],
            [
                [
                    str(r["month"]),
                    str(int(r["case_count"] or 0)),
                    f2(r["total_cost"]),
                    f2(r["avg_cost"]),
                    f2(r["avg_los"]),
                    pct(float(r["avg_drug_ratio"] or 0)),
                ]
                for r in d["monthly"]
            ],
        )
    )
    lines.append("")
    lines.append("医师维度（样本>=20）")
    lines.append(
        md_table(
            ["医生", "病例数", "总费用(元)", "次均费用(元)", "平均住院日", "平均药占比"],
            [
                [
                    str(r["doctor"]),
                    str(int(r["case_count"] or 0)),
                    f2(r["total_cost"]),
                    f2(r["avg_cost"]),
                    f2(r["avg_los"]),
                    pct(float(r["avg_drug_ratio"] or 0)),
                ]
                for r in d["doctor_compare"]
            ],
        )
    )
    lines.append("")
    lines.append("费用结构（费用组）")
    lines.append(
        md_table(
            ["费用组", "金额(元)", "明细条数"],
            [[str(r["cost_group"]), f2(r["total_amount"]), str(int(r["item_count"] or 0))] for r in d["cost_group"]],
        )
    )
    if peak_case_month and peak_cost_month and top_cost_group:
        lines.append(
            f"本步小结：月度病例峰值出现在 {peak_case_month['month']}，次均费用峰值出现在 {peak_cost_month['month']}；"
            f"费用组以 {top_cost_group['cost_group']} 为主（金额 {f2(top_cost_group['total_amount'])} 元）。"
            "建议围绕峰值月份和主导费用组开展针对性复盘。"
        )
    lines.append("")
    if d.get("charts"):
        lines.append("图表可视化（自动生成）")
        for i, chart in enumerate(d["charts"], start=1):
            lines.append(f"**图{i}：{chart['title']}**")
            lines.append(f"![图{i}-{chart['title']}]({chart['md_path']})")
            lines.append(f"说明：{chart['caption']}")
            lines.append("")

    lines.append("### 第3步：找漏洞（费用、效率、合规）")
    lines.append(
        f"- 药占比>=50%：**{d['high_50']}** 例（{pct(d['high_50']/d['case_count']*100 if d['case_count'] else 0)}）；"
        f"药占比>=60%：**{d['high_60']}** 例（{pct(d['high_60']/d['case_count']*100 if d['case_count'] else 0)}）。"
    )
    lines.append(
        f"- 住院日>=14天：**{d['los_14']}** 例（{pct(d['los_14']/d['case_count']*100 if d['case_count'] else 0)}）；"
        f">=21天：**{d['los_21']}** 例（{pct(d['los_21']/d['case_count']*100 if d['case_count'] else 0)}）。"
    )
    lines.append(
        f"- 规则命中：**{d['rule_total']}** 次，涉及患者 **{d['rule_patient_total']}** 人。"
    )
    lines.append(
        md_table(
            ["规则编码", "严重等级", "命中数"],
            [
                [
                    label_rule_code(str(r["rule_code"])),
                    label_severity(str(r["severity"])),
                    str(int(r["hit_count"] or 0)),
                ]
                for r in d["rule_hits"]
            ],
        )
    )
    lines.append("")

    lines.append("DIP映射情况")
    lines.append(
        md_table(
            ["映射状态", "病例数", "占科室病例比"],
            [
                [
                    label_mapping_status(str(r["status"])),
                    str(int(r["cnt"] or 0)),
                    pct(int(r["cnt"] or 0) / d["case_count"] * 100 if d["case_count"] else 0),
                ]
                for r in d["dip_status"]
            ],
        )
    )
    lines.append("")
    lines.append(
        f"说明：DIP已入组 **{d['dip_mapped']}** 例（{pct(d['dip_mapped']/d['case_count']*100 if d['case_count'] else 0)}），"
        f"未入组 **{d['dip_unmapped']}** 例。当前整体入组覆盖率较高，管理重点为未入组个案闭环。"
    )
    lines.append("")
    if d["dip_unmapped_reason"]:
        lines.append("UNMAPPED（未映射）原因分布")
        lines.append(
            md_table(
                ["未入组原因", "病例数", "占科室病例比"],
                [[str(r["fail_reason"]), str(int(r["cnt"] or 0)), pct(int(r["cnt"] or 0) / d["case_count"] * 100 if d["case_count"] else 0)] for r in d["dip_unmapped_reason"]],
            )
        )
        lines.append("")
    lines.append("DIP高权重病种（样本>=5）")
    lines.append(
        md_table(
            ["诊断编码", "诊断名称", "映射病例数", "平均DIP权重", "次均费用(元)", "费用波动CV%"],
            [
                [str(r["diag_code"]), str(r["diag_name"]), str(int(r["mapped_cases"] or 0)), f"{float(r['avg_weight'] or 0):.4f}", f2(r["avg_cost"]), f2(r["cv_cost"])]
                for r in d["dip_weight_top"]
            ],
        )
    )
    lines.append(
        f"本步小结：本期药占比和住院日长尾病例仍需重点监测；规则命中共 {d['rule_total']} 次，"
        f"DIP未映射 {d['dip_unmapped']} 例。建议继续执行“高风险病例周跟踪+未映射个案闭环”管理策略。"
    )
    lines.append("")

    lines.append("### 第4步：定标准（形成整改目标）")
    lines.append(f"- 费用控制基线：次均费用 {f2(d['avg_cost'])} 元，建议下一周期控制在该基线基础上下降3%-5%。")
    lines.append(f"- 效率控制基线：平均住院日 {f2(d['avg_los'])} 天，建议下一周期下降0.5-1.0天。")
    lines.append(f"- 药占比控制基线：{pct(d['avg_drug_ratio'])}，建议下一周期下降1-2个百分点。")
    lines.append(
        f"- DIP管理基线：已映射 {d['dip_mapped']} 例、未映射 {d['dip_unmapped']} 例，建议保持高覆盖并对未映射病例逐案闭环。"
    )
    lines.append(
        "本步小结：已形成费用、效率、用药和DIP管理四类量化基线，具备纳入下周期目标管理与绩效考核的条件。"
    )
    lines.append("")

    lines.append("### 第5步：强闭环（组织与追踪机制）")
    lines.append("- 建议形成“周跟踪、月复盘、季考核”闭环机制。")
    lines.append("- 周度：规则命中清单与未映射病例清单同步下发，责任到人。")
    lines.append("- 月度：对重点病种、重点医师、重点费用组进行复盘并形成整改台账。")
    lines.append("- 季度：对目标达成率、工单闭环率、DIP映射率进行评估，并纳入绩效管理。")
    lines.append("工单现状")
    lines.append(
        md_table(
            ["状态", "数量"],
            [[str(r["status"]), str(int(r["cnt"] or 0))] for r in d["workorders"]],
        )
    )
    lines.append(
        f"本步小结：当前工单总量 {workorder_total} 条。建议按“周监测、月复盘、季评估”机制持续推进，"
        "确保问题发现、责任分配、整改验证和结果复盘形成闭环。"
    )
    lines.append("")

    lines.append("## 四、明细补充")
    lines.append("高金额项目TOP15")
    lines.append(
        md_table(
            ["项目名称", "费用组", "金额(元)", "频次"],
            [[str(r["item_name"]), str(r["cost_group"]), f2(r["total_amount"]), str(int(r["freq"] or 0))] for r in d["top_item"]],
        )
    )
    lines.append("")

    lines.append("## 五、数据口径说明")
    lines.append("- 报告仅使用数据库现存字段。")
    lines.append("- 如人口学字段缺失，则不进行年龄/性别分层，改用病种、费用、住院日、医师、DIP维度替代。")
    return "\n".join(lines) + "\n"


def register_cn_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    for name, path in [("MicrosoftYaHei", r"C:\Windows\Fonts\msyh.ttc"), ("SimHei", r"C:\Windows\Fonts\simhei.ttf"), ("SimSun", r"C:\Windows\Fonts\simsun.ttc")]:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                pass
    return "Helvetica"


def md_to_pdf(md: str, pdf_path: Path, md_base_dir: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font = register_cn_font()
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName=font, fontSize=16, leading=22, spaceAfter=8)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName=font, fontSize=13, leading=18, spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontName=font, fontSize=10, leading=14)
    bullet = ParagraphStyle("bullet", parent=styles["BodyText"], fontName=font, fontSize=10, leading=14, leftIndent=12)

    def split_row(line: str) -> list[str]:
        row = line.strip().strip("|")
        return [c.strip() for c in row.split("|")]

    story = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            story.append(Spacer(1, 5))
            i += 1
            continue
        m = re.match(r"!\[(.*?)\]\((.+?)\)\s*$", line)
        if m:
            alt = m.group(1).strip()
            raw_path = m.group(2).strip().strip("<>")
            p = Path(raw_path)
            if not p.is_absolute():
                p = (md_base_dir / p).resolve()
            if p.exists():
                try:
                    iw, ih = ImageReader(str(p)).getSize()
                    max_w = A4[0] - 72
                    max_h = 300
                    scale = min(max_w / iw, max_h / ih, 1.0)
                    story.append(RLImage(str(p), width=iw * scale, height=ih * scale))
                    if alt:
                        story.append(Paragraph(escape(alt), body))
                    story.append(Spacer(1, 6))
                except Exception:
                    story.append(Paragraph(escape(f"[图像加载失败] {raw_path}"), body))
            else:
                story.append(Paragraph(escape(f"[图像不存在] {raw_path}"), body))
            i += 1
            continue
        if line.startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i].strip())
                i += 1
            if len(block) >= 2:
                header = split_row(block[0])
                rows = [split_row(r) for r in block[2:]]
                data = [[Paragraph(escape(c), body) for c in header]] + [[Paragraph(escape(c), body) for c in row] for row in rows]
                width = (A4[0] - 72) / max(1, len(header))
                table = Table(data, colWidths=[width] * len(header), repeatRows=1)
                table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font), ("FONTSIZE", (0, 0), (-1, -1), 9), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F0F4F8"))]))
                story.append(table)
                story.append(Spacer(1, 6))
            continue
        if line.startswith("# "):
            story.append(Paragraph(escape(line[2:]), h1))
        elif line.startswith("## "):
            story.append(Paragraph(escape(line[3:]), h2))
        elif line.startswith("- "):
            story.append(Paragraph("• " + escape(line[2:]), bullet))
        else:
            story.append(Paragraph(escape(line), body))
        i += 1

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=30, bottomMargin=30)
    doc.build(story)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate department disease report (.md + .pdf)")
    parser.add_argument("--dept", required=True)
    parser.add_argument("--date-from", required=True, help="YYYY-MM-DD")
    parser.add_argument("--date-to", required=True, help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--output-dir", default="docs")
    parser.add_argument("--output-name", default=None)
    parser.add_argument("--db-url", default=None)
    parser.add_argument("--refresh-dip", action="store_true")
    parser.add_argument("--no-charts", action="store_true", help="Disable chart generation/embedding")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    date_from = datetime.strptime(args.date_from, "%Y-%m-%d").date()
    date_to = datetime.strptime(args.date_to, "%Y-%m-%d").date()
    if date_to < date_from:
        raise SystemExit("date-to must be >= date-from")
    date_to_ex = date_to + timedelta(days=1)

    db_url = resolve_db_url(project_root, args.db_url)
    engine = create_engine(db_url, future=True)
    if args.refresh_dip:
        stat = refresh_dip(engine, project_root)
        print(f"[INFO] DIP recalculated: {stat}")

    p = {"dept": args.dept.strip(), "d1": date_from.isoformat(), "d2": date_to_ex.isoformat()}
    with engine.connect() as conn:
        overall = one(conn, "SELECT COUNT(*) case_count,SUM(total_cost) total_cost,AVG(total_cost) avg_cost,AVG(los) avg_los,AVG(drug_cost/NULLIF(total_cost,0))*100 avg_drug_ratio FROM case_info WHERE TRIM(dept_name)=TRIM(:dept) AND discharge_date>=:d1 AND discharge_date<:d2", p)
        if int(overall["case_count"] or 0) == 0:
            raise SystemExit(f"科室“{args.dept}”在时间段内无数据")
        hospital = one(conn, "SELECT COUNT(*) case_count,SUM(total_cost) total_cost,AVG(total_cost) avg_cost,AVG(los) avg_los FROM case_info WHERE discharge_date>=:d1 AND discharge_date<:d2", p)
        monthly = all_rows(conn, "SELECT DATE_FORMAT(discharge_date,'%Y-%m') month,COUNT(*) case_count,SUM(total_cost) total_cost,AVG(total_cost) avg_cost,AVG(los) avg_los,AVG(drug_cost/NULLIF(total_cost,0))*100 avg_drug_ratio FROM case_info WHERE TRIM(dept_name)=TRIM(:dept) AND discharge_date>=:d1 AND discharge_date<:d2 GROUP BY DATE_FORMAT(discharge_date,'%Y-%m') ORDER BY month", p)
        disease_top_cost = all_rows(conn, "SELECT COALESCE(main_diagnosis_code,'(空)') diag_code,MAX(COALESCE(NULLIF(main_diagnosis_name,''),'(未填写)')) diag_name,COUNT(*) case_count,SUM(total_cost) total_cost,AVG(total_cost) avg_cost,STDDEV_POP(total_cost)/NULLIF(AVG(total_cost),0)*100 cv_cost FROM case_info WHERE TRIM(dept_name)=TRIM(:dept) AND discharge_date>=:d1 AND discharge_date<:d2 GROUP BY COALESCE(main_diagnosis_code,'(空)') ORDER BY total_cost DESC LIMIT 10", p)
        doctor_compare = all_rows(conn, "SELECT COALESCE(NULLIF(doctor_name,''),'(未填写)') doctor,COUNT(*) case_count,SUM(total_cost) total_cost,AVG(total_cost) avg_cost,AVG(los) avg_los,AVG(drug_cost/NULLIF(total_cost,0))*100 avg_drug_ratio FROM case_info WHERE TRIM(dept_name)=TRIM(:dept) AND discharge_date>=:d1 AND discharge_date<:d2 GROUP BY COALESCE(NULLIF(doctor_name,''),'(未填写)') HAVING COUNT(*)>=20 ORDER BY case_count DESC", p)
        risk = one(conn, "SELECT SUM(CASE WHEN total_cost>0 AND drug_cost/total_cost>=0.5 THEN 1 ELSE 0 END) high_50,SUM(CASE WHEN total_cost>0 AND drug_cost/total_cost>=0.6 THEN 1 ELSE 0 END) high_60,SUM(CASE WHEN los>=14 THEN 1 ELSE 0 END) los_14,SUM(CASE WHEN los>=21 THEN 1 ELSE 0 END) los_21 FROM case_info WHERE TRIM(dept_name)=TRIM(:dept) AND discharge_date>=:d1 AND discharge_date<:d2", p)
        rule_total = one(conn, "SELECT COUNT(*) hit_count,COUNT(DISTINCT patient_id) patient_count FROM rule_hit WHERE TRIM(dept_name)=TRIM(:dept)", p)
        rule_hits = all_rows(conn, "SELECT rule_code,severity,COUNT(*) hit_count FROM rule_hit WHERE TRIM(dept_name)=TRIM(:dept) GROUP BY rule_code,severity ORDER BY hit_count DESC", p)
        workorders = all_rows(conn, "SELECT status,COUNT(*) cnt FROM work_order WHERE TRIM(dept_name)=TRIM(:dept) GROUP BY status ORDER BY cnt DESC", p)
        dip_status = all_rows(conn, "SELECT COALESCE(d.status,'(无映射记录)') status,COUNT(*) cnt FROM case_info c LEFT JOIN dip_mapping_result d ON d.patient_id=c.patient_id WHERE TRIM(c.dept_name)=TRIM(:dept) AND c.discharge_date>=:d1 AND c.discharge_date<:d2 GROUP BY COALESCE(d.status,'(无映射记录)') ORDER BY cnt DESC", p)
        dip_unmapped_reason = all_rows(conn, "SELECT COALESCE(d.fail_reason,'(空)') fail_reason,COUNT(*) cnt FROM case_info c JOIN dip_mapping_result d ON d.patient_id=c.patient_id WHERE TRIM(c.dept_name)=TRIM(:dept) AND c.discharge_date>=:d1 AND c.discharge_date<:d2 AND d.status='UNMAPPED' GROUP BY COALESCE(d.fail_reason,'(空)') ORDER BY cnt DESC", p)
        dip_weight_top = all_rows(conn, "SELECT COALESCE(c.main_diagnosis_code,'(空)') diag_code,MAX(COALESCE(NULLIF(c.main_diagnosis_name,''),'(未填写)')) diag_name,COUNT(*) mapped_cases,AVG(d.dip_weight_score) avg_weight,AVG(c.total_cost) avg_cost,STDDEV_POP(c.total_cost)/NULLIF(AVG(c.total_cost),0)*100 cv_cost FROM dip_mapping_result d JOIN case_info c ON c.patient_id=d.patient_id WHERE TRIM(c.dept_name)=TRIM(:dept) AND c.discharge_date>=:d1 AND c.discharge_date<:d2 AND d.status='MAPPED' AND d.dip_weight_score IS NOT NULL GROUP BY COALESCE(c.main_diagnosis_code,'(空)') HAVING COUNT(*)>=5 ORDER BY avg_weight DESC LIMIT 10", p)
        cost_group = all_rows(conn, "SELECT COALESCE(cd.cost_group,'(空)') cost_group,SUM(cd.amount) total_amount,COUNT(*) item_count FROM cost_detail cd JOIN case_info c ON c.patient_id=cd.patient_id WHERE TRIM(c.dept_name)=TRIM(:dept) AND c.discharge_date>=:d1 AND c.discharge_date<:d2 GROUP BY COALESCE(cd.cost_group,'(空)') ORDER BY total_amount DESC LIMIT 10", p)
        top_item = all_rows(conn, "SELECT COALESCE(cd.item_name,'(空)') item_name,COALESCE(cd.cost_group,'(空)') cost_group,SUM(cd.amount) total_amount,COUNT(*) freq FROM cost_detail cd JOIN case_info c ON c.patient_id=cd.patient_id WHERE TRIM(c.dept_name)=TRIM(:dept) AND c.discharge_date>=:d1 AND c.discharge_date<:d2 GROUP BY COALESCE(cd.item_name,'(空)'),COALESCE(cd.cost_group,'(空)') ORDER BY total_amount DESC LIMIT 15", p)

        # 同比：上年同期
        yoy_from = shift_year(date_from, -1)
        yoy_to = shift_year(date_to, -1)
        yoy_to_ex = yoy_to + timedelta(days=1)
        p_yoy = {"dept": args.dept.strip(), "d1": yoy_from.isoformat(), "d2": yoy_to_ex.isoformat()}
        yoy_overall = one(
            conn,
            "SELECT COUNT(*) case_count,SUM(total_cost) total_cost,AVG(total_cost) avg_cost,AVG(los) avg_los,AVG(drug_cost/NULLIF(total_cost,0))*100 avg_drug_ratio "
            "FROM case_info WHERE TRIM(dept_name)=TRIM(:dept) AND discharge_date>=:d1 AND discharge_date<:d2",
            p_yoy,
        )

        # 环比：本期末月 vs 上月
        current_month_start = month_start(date_to)
        next_month_start = add_months(current_month_start, 1)
        prev_month_start = add_months(current_month_start, -1)
        p_curr_month = {"dept": args.dept.strip(), "d1": current_month_start.isoformat(), "d2": next_month_start.isoformat()}
        p_prev_month = {"dept": args.dept.strip(), "d1": prev_month_start.isoformat(), "d2": current_month_start.isoformat()}
        curr_month_overall = one(
            conn,
            "SELECT COUNT(*) case_count,SUM(total_cost) total_cost,AVG(total_cost) avg_cost,AVG(los) avg_los,AVG(drug_cost/NULLIF(total_cost,0))*100 avg_drug_ratio "
            "FROM case_info WHERE TRIM(dept_name)=TRIM(:dept) AND discharge_date>=:d1 AND discharge_date<:d2",
            p_curr_month,
        )
        prev_month_overall = one(
            conn,
            "SELECT COUNT(*) case_count,SUM(total_cost) total_cost,AVG(total_cost) avg_cost,AVG(los) avg_los,AVG(drug_cost/NULLIF(total_cost,0))*100 avg_drug_ratio "
            "FROM case_info WHERE TRIM(dept_name)=TRIM(:dept) AND discharge_date>=:d1 AND discharge_date<:d2",
            p_prev_month,
        )

    case_count = int(overall["case_count"] or 0)
    total_cost = float(overall["total_cost"] or 0)
    case_share = case_count / float(hospital["case_count"] or 1) * 100
    cost_share = total_cost / float(hospital["total_cost"] or 1) * 100
    status_map = {str(r["status"]): int(r["cnt"] or 0) for r in dip_status}
    data = {
        "year": date_from.year,
        "dept": args.dept.strip(),
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "case_count": case_count,
        "total_cost": total_cost,
        "avg_cost": float(overall["avg_cost"] or 0),
        "avg_los": float(overall["avg_los"] or 0),
        "avg_drug_ratio": float(overall["avg_drug_ratio"] or 0),
        "case_share": case_share,
        "cost_share": cost_share,
        "disease_top_cost": disease_top_cost,
        "monthly": monthly,
        "doctor_compare": doctor_compare,
        "high_50": int(risk["high_50"] or 0),
        "high_60": int(risk["high_60"] or 0),
        "los_14": int(risk["los_14"] or 0),
        "los_21": int(risk["los_21"] or 0),
        "rule_total": int(rule_total["hit_count"] or 0),
        "rule_patient_total": int(rule_total["patient_count"] or 0),
        "rule_hits": rule_hits,
        "workorders": workorders,
        "dip_status": dip_status,
        "dip_unmapped_reason": dip_unmapped_reason,
        "dip_mapped": status_map.get("MAPPED", 0),
        "dip_unmapped": status_map.get("UNMAPPED", 0),
        "dip_weight_top": dip_weight_top,
        "cost_group": cost_group,
        "top_item": top_item,
        "compare": {
            "yoy_period": [yoy_from.isoformat(), yoy_to.isoformat()],
            "mom_period": [current_month_start.strftime("%Y-%m"), prev_month_start.strftime("%Y-%m")],
            "case_count": {
                "curr": case_count,
                "yoy_base": int(yoy_overall["case_count"] or 0),
                "yoy_pct": pct_change(case_count, int(yoy_overall["case_count"] or 0)),
                "mom_base": int(prev_month_overall["case_count"] or 0),
                "mom_pct": pct_change(int(curr_month_overall["case_count"] or 0), int(prev_month_overall["case_count"] or 0)),
            },
            "total_cost": {
                "curr": total_cost,
                "yoy_base": float(yoy_overall["total_cost"] or 0),
                "yoy_pct": pct_change(total_cost, float(yoy_overall["total_cost"] or 0)),
                "mom_base": float(prev_month_overall["total_cost"] or 0),
                "mom_pct": pct_change(float(curr_month_overall["total_cost"] or 0), float(prev_month_overall["total_cost"] or 0)),
            },
            "avg_cost": {
                "curr": float(overall["avg_cost"] or 0),
                "yoy_base": float(yoy_overall["avg_cost"] or 0),
                "yoy_pct": pct_change(float(overall["avg_cost"] or 0), float(yoy_overall["avg_cost"] or 0)),
                "mom_base": float(prev_month_overall["avg_cost"] or 0),
                "mom_pct": pct_change(float(curr_month_overall["avg_cost"] or 0), float(prev_month_overall["avg_cost"] or 0)),
            },
            "avg_los": {
                "curr": float(overall["avg_los"] or 0),
                "yoy_base": float(yoy_overall["avg_los"] or 0),
                "yoy_pct": pct_change(float(overall["avg_los"] or 0), float(yoy_overall["avg_los"] or 0)),
                "mom_base": float(prev_month_overall["avg_los"] or 0),
                "mom_pct": pct_change(float(curr_month_overall["avg_los"] or 0), float(prev_month_overall["avg_los"] or 0)),
            },
            "avg_drug_ratio": {
                "curr": float(overall["avg_drug_ratio"] or 0),
                "yoy_base": float(yoy_overall["avg_drug_ratio"] or 0),
                "yoy_pct": pct_change(float(overall["avg_drug_ratio"] or 0), float(yoy_overall["avg_drug_ratio"] or 0)),
                "mom_base": float(prev_month_overall["avg_drug_ratio"] or 0),
                "mom_pct": pct_change(float(curr_month_overall["avg_drug_ratio"] or 0), float(prev_month_overall["avg_drug_ratio"] or 0)),
            },
        },
    }

    out_dir = (project_root / args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    base = safe_name(args.output_name or f"{args.dept}_{date_from}_{date_to}_病种分析报告")
    charts = [] if args.no_charts else generate_charts(data, out_dir, base)
    data["charts"] = charts

    md = build_markdown(data)
    md_path = out_dir / f"{base}.md"
    pdf_path = out_dir / f"{base}.pdf"
    md_path.write_text(md, encoding="utf-8-sig")
    md_to_pdf(md, pdf_path, md_path.parent)

    print("[OK] report generated")
    print(f"MD : {md_path}")
    print(f"PDF: {pdf_path}")
    if charts:
        print(f"CHARTS: {len(charts)} files in {out_dir / (base + '_charts')}")


if __name__ == "__main__":
    main()
