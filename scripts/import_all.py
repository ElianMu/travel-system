"""批量导入 data/ 目录下所有文档（先预热模型，规避原生库冲突）。"""
import os

from app.rag.embedder import embed

embed(["预热"])  # 预热 Embedding 模型

from app.services.import_service import get_task, import_document  # noqa: E402

DATA_DIR = "data"


def main() -> None:
    files = []
    for root, _dirs, names in os.walk(DATA_DIR):
        for name in sorted(names):
            if name.endswith(".md"):
                files.append(os.path.join(root, name))

    print(f"共 {len(files)} 份文档待导入")
    ok = fail = 0
    for i, path in enumerate(files, 1):
        name = os.path.basename(path)
        try:
            tid = import_document(path, source_file=name)
            st = get_task(tid)
            if st and st["status"] == "success":
                ok += 1
                print(f"[{i}/{len(files)}] {name} 成功（{st['processed_chunks']} chunks）")
            else:
                fail += 1
                print(f"[{i}/{len(files)}] {name} 失败：{st and st.get('error_message')}")
        except Exception as exc:  # noqa: BLE001
            fail += 1
            print(f"[{i}/{len(files)}] {name} 异常：{exc}")

    print(f"\n导入完成：成功 {ok}，失败 {fail}")


if __name__ == "__main__":
    main()
