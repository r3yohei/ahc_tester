import os
import argparse
import tomllib

import ray

from src.test import parallel_test, single_test
from src.optimize_hyperparameter import run_optuna


def main():
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='AHC Tester')
    parser.add_argument("contest", help="contest numbering", type=str)
    parser.add_argument("-pl", "--platform", help="contest platform", type=str, choices=["atcoder", "yukicoder"], default="atcoder")
    parser.add_argument("-i", "--interactive", help="interactive or not", action="store_true")
    parser.add_argument("-v", "--visualizer", help="use visualizer for calculating score", action="store_true")
    parser.add_argument("-b", "--build", help="build source code", action="store_true")
    parser.add_argument("-fb", "--force-build", help="forcely build tester code", action="store_true")
    parser.add_argument("-s", "--single", help="test a given id case", type=int, default=None)
    parser.add_argument("-bs", "--binary-suffix", help="binary suffix. default is 'a' in atcoder", type=str, default="a")
    parser.add_argument("-n", help="num of test cases", type=int, default=None)
    parser.add_argument("-pr", "--parameter", help="parameter names given by a contest", nargs="+", type=str, default=None)
    parser.add_argument("-d", "--directory", help="name of testcase directory", type=str, default="")
    parser.add_argument("-o", "--optuna", help="optimize hyperparameters with optuna", action="store_true")
    parser.add_argument("-on", "--optuna-n-trials", help="optuna n_trials", type=int, default=100)
    parser.add_argument("-od", "--optuna-direction", help="optimizing direction", type=str, default="maximize")
    parser.add_argument("-ost", "--optuna_score_type", help="optimize with absolute or relative score", type=str, choices=["a", "r"], default="r")
    parser.add_argument("-g", "--gen", help="num of generating testcases", type=int, default=None)
    args = parser.parse_args()


    # バリデーション
    if not os.path.exists(f"../{args.contest}"):
        print(f"contest directory {args.contest} does not exists")
        exit(1)
    if not os.path.exists(f"../{args.contest}/tools"):
        print(f"{args.contest} local tester does not exists. please download from atcoder.")
        exit(1)
    if not os.path.exists(f"../{args.contest}/tools/out{args.directory}"):
        print(f"making tester output directory as {args.contest}/tools/out{args.directory}.")
        os.makedirs(f"../{args.contest}/tools/out{args.directory}")
    
    if args.build:
        # optunaを回す前にCargo.tomlにRustのコマンドライン引数解析クレートであるclapが入っているか確認する
        if args.optuna:
            with open(f"../{args.contest}/Cargo.toml", mode="rb") as f:
                toml = tomllib.load(f)
            if not "clap" in toml["dependencies"]:
                os.chdir(f"../{args.contest}")
                # v1.70.0用を指定することと，--features deriveでderive形式を使えるものを指定することに注意
                os.system("cargo add clap@=4.4.18 --features derive")

        # 配布ローカルテスターをビルド
        visualizer = "../../../target/release/vis"
        # 強制ビルドか，存在しないか，コンテストディレクトリより古い(=過去のテスター)ならビルドする
        if args.force_build or not os.path.exists(visualizer) or (os.path.exists(visualizer) and os.stat(visualizer).st_mtime < os.stat(f"../{args.contest}").st_mtime):
            print("building local tester...")
            os.chdir(f"../{args.contest}/tools")
            os.system("cargo clean -r")
            os.system("cargo build -r")
            os.chdir("..")

        # 自前のソースコードをビルド
        print("building source code...")
        os.chdir(f"../{args.contest}")
        os.system("cargo build -r")

    os.chdir(f"../{args.contest}")
    if args.optuna and args.n is not None:
        # プログラム内のハイパーパラメータをoptunaで最適化する
        run_optuna(args)
    elif args.n is not None:
        # [0,n)のテストケースを実行する
        parallel_test(args)
    elif args.single is not None:
        # 指定のテストケースを1つ実行する
        single_test(args.single, args)

    # テストケースを増やす
    if args.gen is not None:
        print(f"generating {args.gen} test cases...")
        with open(f"../{args.contest}/tools/seeds.txt", "w") as f:
            for i in range(args.gen):
                f.write("{}\n".format(i))

        generator = "../../../target/release/gen"
        # 強制ビルドか，存在しないか，コンテストディレクトリより古い(=過去のテスター)ならビルドする
        if args.force_build or not os.path.exists(generator) or (os.path.exists(generator) and os.stat(generator).st_mtime < os.stat(f"../{args.contest}").st_mtime):
            print("building generator...")
            os.chdir(f"../{args.contest}/tools")
            os.system("cargo clean -r")
            os.system("cargo build -r")
            os.chdir("..")
        
        os.chdir(f"../{args.contest}/tools")
        if len(args.directory) > 0:
            # 複数問のテストケースへの対応
            os.system(f"../{generator} ./seeds.txt --problem {args.directory} --dir=in{args.directory}")
        else:
            os.system(f"../{generator} ./seeds.txt")
        os.chdir("..")


if __name__ == '__main__':
    main()