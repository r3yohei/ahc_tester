import os
import subprocess
import time

import pandas as pd
import ray


@ray.remote
def single_test(i, args):
    # tester or 自プログラム or visualizer からスコアの取得を試みる
    if args.visualizer:
        visualizer = "../../../target/release/vis"
        proc = subprocess.Popen(
            f"{visualizer} < ../{args.contest}/tools/in/{i:04d}.txt > ../{args.contest}/tools/out/{i:04d}.txt",
            shell=True,
            stderr=subprocess.PIPE,
            text=True
        )
    else:
        if args.interactive:
            tester = "../../../target/release/tester"
        else:
            tester = ""
        testee = f"../../../target/release/{args.contest}-a"
        proc = subprocess.Popen(
            f"{tester} {testee} < ../{args.contest}/tools/in/{i:04}.txt > ../{args.contest}/tools/out/{i:04}.txt",
            shell=True,
            stderr=subprocess.PIPE,
            text=True
        )

    # 標準エラーからスコアやパラメータを探す
    param_dict = dict()
    content = proc.stderr.read()
    print(content)
    for c in content.split("\n"):
        if "score" in c or "Score" in c:
            score = c.split(" ")[-1]
        if args.parameter is not None:
            for p in args.parameter:
                if p in c:
                    # [注]パラメータ名にSなど，Scoreの行にもヒットしてしまうものがある場合は適宜ワークアラウンドすること
                    param_dict[p] = c.split(" ")[-1]

    if score is not None:
        # seriesを作って返す
        data = [i, score]
        index = ["case", "score"]
        if args.parameter is not None:
            for p in args.parameter:
                data.append(param_dict[p])
                index.append(p)
        
        return pd.Series(data=data, index=index)
    else:
        print("cannot get score")
        exit(1)

def test(args):
    print(f"testing {args.n} cases...")
    start = time.time()
    ray.init(num_cpus=10)
    # テスト結果を格納するディレクトリを作る
    os.makedirs(f"../{args.contest}/tools/out", exist_ok=True)
    os.makedirs(f"../{args.contest}/result", exist_ok=True)

    # テストの並列実行
    proc_list = []
    for i in range(args.n):
        proc_list.append(single_test.remote(i, args))

    series_list = ray.get(proc_list)
    result_df = pd.DataFrame(series_list)
    current_time = time.strftime("%Y_%m_%d-%H_%M_%S", time.localtime())
    result_df.to_csv(f"../{args.contest}/result/{current_time}.csv", index=False)

    print("test finished")
    print(f"elapsed: {time.time() - start}")