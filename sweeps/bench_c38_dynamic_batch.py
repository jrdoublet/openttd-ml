"""Banc apparié C38 : batch dynamique contre défaut, 20 graines x 10 ans."""
import bench_c36_1_portfolio_cache as bench

bench.ARMS = ("OpexAI", "OpexAI[portfolio_dynamic_batch=1]")


if __name__ == "__main__":
    bench.main()
