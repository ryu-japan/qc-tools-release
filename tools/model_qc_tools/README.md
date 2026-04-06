# Model QC Tools

Maya 用のモデル品質チェックツール。メッシュのジオメトリ・シーン構成・セットアップを包括的にチェックし、検出結果の確認・選択をインタラクティブに行える。

## 基本の流れ

1. チェック対象の **メッシュを選択**（トップノード選択で子メッシュを自動収集）
2. **ターゲットモード** を選択（Visible Meshes / Selected Meshes / Group）
3. **Model タブ** または **Setup タブ** でチェック項目を確認
4. **Check** ボタンを実行（アクティブタブの有効項目を一括実行）
5. 結果ウィンドウでエラーを確認・選択
6. すべてのチェックは非同期で実行され、プログレスバーで進捗を確認できる。処理中は×ボタンでキャンセル可能。

---

## ターゲットモード

- **Visible Meshes**（デフォルト）: シーン内の表示中メッシュすべて
- **Selected Meshes**: 選択中のメッシュ（階層展開あり）
- **Group**: 指定グループ配下のメッシュ。Set ボタンで選択ノードを取得

---

## チェック項目

チェック項目は **3層構造** で管理され、各タブ内で層ごとに折りたたみ表示される。

- **🔒 必須**: 常時実行・OFF 不可
- **✅ 標準**: デフォルト ON・OFF 可
- **⚙️ オプション**: デフォルト OFF・ON 可

### Model タブ（22項目）

**🔒 必須（7）** — Lamina faces / Nonmanifold geometry / Zero geometry / Invalid components / Reversed normals / Overlapping vertices / Ngons (5+ sided)

**✅ 標準（7）** — Invalid face shapes / Remaining history / Unfreezed transforms / Unused nodes & empty groups / Naming check / Unassigned materials / Remaining instances

**⚙️ オプション（8）** — Triangulation check / Non-planar faces / Symmetry mismatch / Edge misalignment / Polygon count exceeded / Vertex color check / Scene units & Up-axis check / Origin check

### Setup タブ（4項目）

**🔒 必須（1）** — Joint rotate zero check

**✅ 標準（2）** — Weight precision & Influence count / Joint orient direction check

**⚙️ オプション（1）** — Bone symmetry check

---

## 結果ウィンドウ

- 項目クリック: 該当箇所がビューポートで選択される
- **すべて選択**: 全エラーを一括選択
- エラーなし → 「エラーなし ✔」ダイアログを表示
- ステータスバーにチェック名と処理時間を表示
