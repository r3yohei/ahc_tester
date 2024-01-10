# Test Tools for AtCoder Heuristic Contest
## 概要
- Rust用AHCのテストツールです

## 使い方
- リポジトリのクローン
    - ahcのプロジェクトとの階層関係は以下のようにする
```
$ tree -L 1
.
|-- ahc001
|   |-- Cargo.lock
|   |-- Cargo.toml
|   |-- src
|   `-- testcases
|-- ahc002
|   |-- Cargo.lock
|   |-- Cargo.toml
|   |-- src
|   `-- testcases
`-- ahc_tester
    |-- LICENSE
    |-- README.md
    |-- main.py
    |-- src
    `-- visualize.ipynb
```
- テスト実行
    - インタラクティブかどうかなどをコマンドライン引数で指定可能
```bash
cd ahc_tester
python main.py ahcXXX -b -n 100
```
- optuna
    - 事前に`ahcXXX/hyperparameter.yaml`を用意してハイパーパラメータの探索空間を定義しておくこと
```bash
python main.py ahcXXX -b -n 100 -o
```
- テストケース生成
```bash
python main.py ahcXXX -g 1000
```