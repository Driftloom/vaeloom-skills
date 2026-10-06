#!/usr/bin/env python3
"""Total Compensation (TC) Calculator Script.

Calculates annualized and 4-year Total Compensation across:
- Base Salary
- Annual Bonus Target
- Public RSUs vs Private ISOs/NSOs
- Signing Bonus
"""
from __future__ import annotations

import argparse
import json
import sys


def calculate_total_comp(
    base: float,
    bonus_pct: float = 0.0,
    rsu_grant_value: float = 0.0,
    vesting_years: float = 4.0,
    signing_bonus: float = 0.0,
    options_count: int = 0,
    options_strike: float = 0.0,
    options_fair_value: float = 0.0,
) -> dict:
    annual_bonus = base * (bonus_pct / 100.0)
    annual_rsu = rsu_grant_value / vesting_years if vesting_years > 0 else 0.0

    # Startup options spread valuation
    option_spread = max(0.0, options_fair_value - options_strike)
    total_options_value = options_count * option_spread
    annual_options = total_options_value / vesting_years if vesting_years > 0 else 0.0

    annual_equity = annual_rsu + annual_options
    total_equity_grant = rsu_grant_value + total_options_value

    year_1_tc = base + annual_bonus + annual_equity + signing_bonus
    steady_state_tc = base + annual_bonus + annual_equity
    four_year_total = (base + annual_bonus) * 4.0 + total_equity_grant + signing_bonus

    return {
        "inputs": {
            "base_salary": round(base, 2),
            "bonus_percentage": bonus_pct,
            "annual_bonus": round(annual_bonus, 2),
            "equity_grant_total": round(total_equity_grant, 2),
            "vesting_years": vesting_years,
            "signing_bonus": round(signing_bonus, 2),
        },
        "annualized": {
            "year_1_total_compensation": round(year_1_tc, 2),
            "steady_state_total_compensation": round(steady_state_tc, 2),
            "annual_equity_amortized": round(annual_equity, 2),
        },
        "multi_year": {
            "four_year_cumulative_comp": round(four_year_total, 2),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Total Compensation Calculator")
    parser.add_argument("--base", type=float, required=True, help="Annual base salary in USD")
    parser.add_argument("--bonus-pct", type=float, default=0.0, help="Target bonus percentage (e.g. 15 for 15%)")
    parser.add_argument("--equity", type=float, default=0.0, help="Total 4-year RSU grant value in USD")
    parser.add_argument("--signing", type=float, default=0.0, help="One-time signing bonus in USD")
    parser.add_argument("--years", type=float, default=4.0, help="Vesting schedule duration in years")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    result = calculate_total_comp(
        base=args.base,
        bonus_pct=args.bonus_pct,
        rsu_grant_value=args.equity,
        vesting_years=args.years,
        signing_bonus=args.signing,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        inp = result["inputs"]
        ann = result["annualized"]
        print("=== TOTAL COMPENSATION BREAKDOWN ===")
        print(f"Base Salary:               ${inp['base_salary']:,.2f}")
        print(f"Annual Bonus ({inp['bonus_percentage']}%):         ${inp['annual_bonus']:,.2f}")
        print(f"Annual Equity (1/{int(inp['vesting_years'])}):       ${ann['annual_equity_amortized']:,.2f}")
        print(f"Signing Bonus (Yr 1):      ${inp['signing_bonus']:,.2f}")
        print("------------------------------------")
        print(f"Year 1 Total Comp:         ${ann['year_1_total_compensation']:,.2f}")
        print(f"Steady State Annual Comp:  ${ann['steady_state_total_compensation']:,.2f}")
        print(f"4-Year Cumulative Total:   ${result['multi_year']['four_year_cumulative_comp']:,.2f}")


if __name__ == "__main__":
    main()
