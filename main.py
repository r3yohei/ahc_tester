import os
import argparse

from src.test import test
from src.optimize_hyperparameter import run_optuna


def main():
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='AHC Tester')
    parser.add_argument("contest", help="contest numbering", type=str)
    parser.add_argument("-i", "--interactive", help="interactive or not", action="store_true")
    parser.add_argument("-v", "--visualizer", help="use visualizer for calculating score", action="store_true")
    parser.add_argument("-b", "--build", help="build source code", action="store_true")
    parser.add_argument("-n", help="num of test cases", type=int, default=None)
    parser.add_argument("-p", "--parameter", help="parameter names given by a contest", nargs="+", type=str, default=None)
    parser.add_argument("-o", "--optuna", help="optimize hyperparameters with optuna", action="store_true")
    parser.add_argument("-on", "--optuna-n-trials", help="optuna n_trials", type=int, default=100)
    parser.add_argument("-od", "--optuna-direction", help="optimizing direction", type=str, default="maximize")
    parser.add_argument("-g", "--gen", help="num of generating testcases", type=int, default=None)
    args = parser.parse_args()


    # バリデーション
    if not os.path.exists(f"../{args.contest}"):
        print(f"contest directory {args.contest} does not exists")
        exit(1)
    
    if args.build:
        # 自前のソースコードをビルド
        print("building source code...")
        os.chdir(f"../{args.contest}")
        os.system("cargo build -r")

        # 配布ローカルテスターをビルド
        visualizer = "../../../target/release/vis"
        # 存在しないか，コンテストディレクトリより古い(=過去のテスター)ならビルドする
        if not os.path.exists(visualizer) or (os.path.exists(visualizer) and os.stat(visualizer).st_mtime < os.stat(f"../{args.contest}").st_mtime):
            print("building local tester...")
            os.chdir(f"../{args.contest}/tools")
            os.system("cargo build -r")
            os.chdir("..")

        print("finished")

    os.chdir(f"../{args.contest}")
    if args.optuna and args.n is not None:
        # プログラム内のハイパーパラメータをoptunaで最適化する
        run_optuna(args)
    elif args.n is not None:
        # 指定のテストケースを実行する
        test(args)

    # テストケースを増やす
    if args.gen is not None:
        with open(f"../{args.contest}/tools/seeds.txt", "w") as f:
            for i in range(args.gen):
                f.write("{}\n".format(i))

        generator = "../../../target/release/gen"
        # 存在しないか，コンテストディレクトリより古い(=過去のテスター)ならビルドする
        if not os.path.exists(generator) or (os.path.exists(generator) and os.stat(generator).st_mtime < os.stat(f"../{args.contest}").st_mtime):
            print("building generator...")
            os.chdir(f"../{args.contest}/tools")
            os.system("cargo build -r")
            os.chdir("..")
        
        os.chdir(f"../{args.contest}/tools")
        os.system(f"../{generator} ./seeds.txt")
        os.chdir("..")


if __name__ == '__main__':
    main()