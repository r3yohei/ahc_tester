import os
import subprocess
import time
import math

import pandas as pd
import ray


@ray.remote
def parallel_test_func(i, args):
    # tester or 自プログラム or visualizer からスコアの取得を試みる
    if args.visualizer:
        visualizer = "../../../target/release/vis"
        proc = subprocess.Popen(
            f"{visualizer} ../{args.contest}/tools/in{args.directory}/{i:04d}.txt ../{args.contest}/tools/out{args.directory}/{i:04d}.txt",
            shell=True,
            stderr=subprocess.PIPE,
            text=True
        )
    else:
        if args.interactive:
            tester = "../../../target/release/tester"
        else:
            tester = ""
        if args.platform == "atcoder":
            testee = f"../../../target/release/{args.contest}-{args.binary_suffix}"
        elif args.platform == "yukicoder":
            testee = f"../../../target/release/contest{args.contest}-{args.binary_suffix}"
        proc = subprocess.Popen(
            f"exec {tester} {testee} < ../{args.contest}/tools/in{args.directory}/{i:04}.txt > ../{args.contest}/tools/out{args.directory}/{i:04}.txt",
            shell=True,
            stderr=subprocess.PIPE,
            text=True
        )

    # 標準エラーからスコアやパラメータを探す
    param_dict = dict()
    content = proc.stderr.read()
    print(content)
    score = None
    for c in content.split("\n"):
        if "panicked" in c:
            print(f"error occurs in case {i:04}")
            proc.kill()
        if "score" in c or "Score" in c:
            score = c.split(" ")[-1]
        if args.parameter is not None:
            for p in args.parameter:
                if p in c:
                    # [注]パラメータ名にSなど，Scoreの行にもヒットしてしまうものがある場合は適宜ワークアラウンドすること
                    param_dict[p] = c.split(" ")[-1]

    if score is not None:
        # seriesを作って返す
        data = [i, score, math.log10(1 + int(score))]
        index = ["case", "score", "log_score"]
        if args.parameter is not None:
            for p in args.parameter:
                data.append(param_dict[p])
                index.append(p)
        
        return pd.Series(data=data, index=index)
    else:
        print(f"cannot get score in case {i:04}")
        return None

def parallel_test(args):
    print(f"testing {args.n} cases...")
    start = time.time()
    ray.init(num_cpus=10)
    # テスト結果を格納するディレクトリを作る
    os.makedirs(f"../{args.contest}/tools/out{args.directory}", exist_ok=True)
    os.makedirs(f"../{args.contest}/result{args.directory}", exist_ok=True)

    # テストの並列実行
    proc_list = []
    for i in range(args.n):
        tmp_series = parallel_test_func.remote(i, args)
        if tmp_series is not None:
            proc_list.append(tmp_series)

    series_list = ray.get(proc_list)
    result_df = pd.DataFrame(series_list)
    current_time = time.strftime("%Y_%m_%d-%H_%M_%S", time.localtime())
    result_df.to_csv(f"../{args.contest}/result{args.directory}/{current_time}.csv", index=False)

    print("test finished")
    print(f"elapsed: {time.time() - start}")

def single_test(i, args):
    # 非並列の単ケーステスト
    print(f"testing case id {i}...")
    if args.visualizer:
        visualizer = "../../../target/release/vis"
        proc = subprocess.Popen(
            f"{visualizer} ../{args.contest}/tools/in{args.directory}/{i:04d}.txt ../{args.contest}/tools/out{args.directory}/{i:04d}.txt",
            shell=True,
            stderr=subprocess.PIPE,
            text=True
        )
    else:
        if args.interactive:
            tester = "../../../target/release/tester"
        else:
            tester = ""
        if args.platform == "atcoder":
            testee = f"../../../target/release/{args.contest}-{args.binary_suffix}"
        elif args.platform == "yukicoder":
            testee = f"../../../target/release/contest{args.contest}-{args.binary_suffix}"
        proc = subprocess.Popen(
            f"{tester} {testee} < ../{args.contest}/tools/in{args.directory}/{i:04}.txt > ../{args.contest}/tools/out{args.directory}/{i:04}.txt",
            shell=True,
            stderr=subprocess.PIPE,
            text=True
        )

    # subprocessからpollingの応答がなくなるまで標準エラーを出力し続ける
    while proc.poll() is None:
        for line in proc.stderr.read().splitlines():
            print(line)