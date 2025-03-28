import os
import subprocess
import json
import time
import math
import yaml
import statistics

import ray
import optuna


@ray.remote
def single_test(i, args, hyperparameters):
    if args.interactive:
            tester = "../../../target/release/tester"
    else:
        tester = ""
    # optunaという名前のバイナリを作る想定
    testee = f"../../../target/release/optuna"

    # clapクレートを使う想定のため，コマンドライン引数が続くことを示す--を記載
    command = f"{tester} {testee} < ../{args.contest}/tools/in{args.directory}/{i:04}.txt > /dev/null --"
    # ハイパーパラメータを文字列に結合し，subprocessにrustを実行させる
    for hp in hyperparameters:
        command += f" {hp}"
    proc = subprocess.Popen(
        command,
        shell=True,
        stderr=subprocess.PIPE,
        text=True
    )

    content = proc.stderr.read()
    score = None
    for c in content.split("\n"):
        if "score" in c or "Score" in c:
            score = c.split(" ")[-1]

    if score is not None:
        if args.optuna_score_type == "a":
            # 絶対スコア
            return int(score)
        else:
            # 相対スコア
            return math.log10(1 + int(score))
    else:
        # scoreが取れないとき
        if args.optuna_direction == "maximize":
            # 方向がmaximizeなら，0点とする
            return 0
        else:
            # 方向がminimizeなら，INF点とする
            return 1e10

def objective_wrapper(args, hyperparameters):

    def objective(trial: optuna.trial.Trial):
        start = time.time()

        # yamlで与えられた探索空間でsuggestする
        suggested_hyperparameters = []
        for hp in hyperparameters:
            if hp["type"] == "int":
                v = trial.suggest_int(hp["name"], int(hp["low"]), int(hp["high"]))
            elif hp["type"] == "float":
                v = trial.suggest_float(hp["name"], float(hp["low"]), float(hp["high"]))

            suggested_hyperparameters.append(v)

        # 並列実行
        proc_list = []
        for i in range(args.n):
            proc_list.append(single_test.remote(i, args, suggested_hyperparameters))

        score_list = ray.get(proc_list)

        print(f"elapsed: {time.time() - start}")

        return statistics.mean(score_list)
    
    return objective


def run_optuna(args):
    print("optimizing hyperparameters...")
    start = time.time()
    ray.init(num_cpus=4)
    # ハイパーパラメータの探索空間定義を取得
    if not os.path.exists(f"../{args.contest}/hyperparameter{args.directory}.yaml"):
        print(f"hyperparameter{args.directory}.yaml does not exists")
        exit(1)
    with open(f"../{args.contest}/hyperparameter{args.directory}.yaml", "r") as f:
        hyperparameter_yaml = yaml.safe_load(f)

    # ahcXXX-aではなく，optunaという名前のバイナリを別で用意すること
    testee = f"../../../target/release/optuna"
    if not os.path.exists(testee):
        print("binary named optuna does not exists")
        exit(1)

    # スコアの最大化か最小化かに注意
    if args.optuna_initial and os.path.exists(f"../{args.contest}/initial_hyperparameter.json"):
        # 初期値利用
        with open(f"../{args.contest}/initial_hyperparameter.json", "r") as f:
            initial = json.load(f)
        study = optuna.create_study(
            study_name=f"{args.contest}{args.directory}",
            direction=args.optuna_direction,
            storage=f"sqlite:///{args.contest}{args.directory}.db",
            sampler=optuna.samplers.TPESampler(),
            pruner=optuna.pruners.MedianPruner(),
        )
        study.enqueue_trial(initial)
    else:
        study = optuna.create_study(
            study_name=f"{args.contest}{args.directory}",
            direction=args.optuna_direction,
            storage=f"sqlite:///{args.contest}{args.directory}.db",
            load_if_exists=True,
            sampler=optuna.samplers.TPESampler(),
            pruner=optuna.pruners.MedianPruner()
        )
    study.optimize(objective_wrapper(args, hyperparameter_yaml["hyperparameter"]), n_trials=args.optuna_n_trials)
    
    # 最適化結果の保存
    os.makedirs(f"../{args.contest}/optimized_hyperparameter{args.directory}", exist_ok=True)
    current_time = time.strftime("%Y_%m_%d-%H_%M_%S", time.localtime())
    with open(f"../{args.contest}/optimized_hyperparameter{args.directory}/{current_time}.json", "w") as f:
        json.dump(study.best_params, f, indent=4)

    print("optimization finished")
    print(f"elapsed: {time.time() - start}")