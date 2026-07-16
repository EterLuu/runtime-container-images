# 运行环境镜像发布流程

本文档说明如何维护和发布 `images/<platform>/<runtime>/*` 下的运行环境镜像。流程是：PR 中完成构建验证，合并后通过手动 workflow 发布镜像。

目录前两级会用于发布分类：`images/modelarts/cann/...` 发布到 `modelarts-cann`，`images/modelarts/cuda/...` 发布到 `modelarts-cuda`。

## 1. 目录和标签

推荐目录格式：

```text
images/<platform>/<runtime>/<tag>/Dockerfile
```

当前示例：

```text
images/modelarts/cann/9.0.0-910b-ubuntu22.04/Dockerfile
images/modelarts/cuda/12.6.1-v100-ubuntu24.04/Dockerfile
```

CANN 模板可以通过 `chip` 和 `derived_chips` 自动衍生 tag：

```text
9.0.0-310p-ubuntu22.04
9.0.0-910-ubuntu22.04
9.0.0-950-ubuntu22.04
9.0.0-a3-ubuntu22.04
```

衍生过程只替换 Dockerfile 顶层 `BASE_IMAGE`。没有 `chip` 的镜像不会做芯片衍生，直接按目录 tag 构建。

构建前会自动把同类型目录下的 `scripts/` 复制到目标构建目录的 `scripts/` 下，例如 `images/modelarts/cuda/scripts` 会复制到 `images/modelarts/cuda/<tag>/scripts`。

## 2. 新增或更新镜像

1. 在 `images/<platform>/<runtime>/<tag>/Dockerfile` 新增或修改 Dockerfile。
2. 可选更新 `image_publish_version.json`：
   - `path` 指向 Dockerfile 所在目录。
   - `tags` 写入要发布的 tag 列表。
   - `image_version` 用于批量发布筛选。
   - `chip` 和 `derived_chips` 用于 CANN 这类可替换芯片字段的模板。
   - `base_image` 写模板基础镜像，衍生芯片会自动替换其中的芯片字段。
   - `arches` 定义目标平台和 GitHub Actions runner。
3. 如果需要更新容器启动或 SSH 逻辑，修改同类型目录下的 `scripts`，不要提交生成到 `images/<platform>/<runtime>/<tag>/scripts` 下的副本。
4. 本地执行校验：

```bash
python3 scripts/image_metadata.py validate
```

5. 可选，本地构建验证：

```bash
IMAGE_REPOSITORY=modelarts-cuda \
  scripts/build_image.sh 12.6.1-v100-ubuntu24.04
```

## 3. PR 构建验证

提交 PR 后，`Build Images` 会自动运行：

- 校验 `image_publish_version.json` 和实际 Dockerfile 目录。
- 只为实际存在的 `images/<platform>/<runtime>/<tag>` 目录和目标平台生成 matrix，不展开 `derived_chips`。
- 使用 `docker/build-push-action` 构建镜像，但不推送。

CUDA 样例没有显式配置 `arches` 时默认只构建 `linux/amd64`。其它运行环境默认使用 `linux/amd64` 和 `linux/arm64`，也可以在 `image_publish_version.json` 中覆盖。

## 4. 发布单个镜像

在 GitHub Actions 页面手动运行 `Build and Publish Image`：

| 参数                 | 说明                                                                      |
| -------------------- | ------------------------------------------------------------------------- |
| `image_tag`          | 要发布的 tag                                                              |
| `image_key`          | 可选，存在多个分类使用同名 tag 时填写 `images/<platform>/<runtime>/<tag>` |
| `publish`            | `true` 时推送镜像；`false` 时只构建                                       |
| `image_repositories` | 发布目标仓库，留空时使用仓库变量 `IMAGE_REPOSITORIES`，再回退到默认 GHCR  |

发布到多个仓库时使用逗号或空白分隔：

```text
ghcr.io/<owner>,docker.io/<namespace>,quay.io/<namespace>,swr.cn-southwest-2.myhuaweicloud.com/<organization>
```

仓库名会自动转换为小写。填写命名空间或基础仓库时，发布脚本会按镜像目录自动补齐或替换末级仓库名。例如发布 `images/modelarts/cuda/...` 时，`swr.cn-southwest-2.myhuaweicloud.com/<organization>` 会变成 `swr.cn-southwest-2.myhuaweicloud.com/<organization>/modelarts-cuda`。

`IMAGE_REPOSITORIES` 和 `image_repositories` 只能包含镜像仓库地址，不要写入用户名、密码、token 或 URL scheme。登录凭据必须放在 Secrets 中。

发布流程会先按架构推送 digest，再创建并推送最终 manifest list。每次发布会同时更新基础版本 tag、带 Release 标记的 tag 和 `latest`，例如 `9.0.0-910b-ubuntu22.04`、`9.0.0-910b-ubuntu22.04-r260716.122328` 和 `latest`。Release 标记格式为 `rYYMMDD.HHMMSS`，同一次批量发布共享同一个时间戳；本地发布可通过 `RELEASE_TIMESTAMP=YYMMDD.HHMMSS` 指定。批量发布多个镜像到同一仓库时，`latest` 最终指向最后完成发布的镜像。

## 5. 批量发布

运行 `Batch Build and Publish Images`：

| 参数                 | 说明                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------- |
| `image_version`      | 匹配 `image_publish_version.json` 中的 `image_version`，或从目录 tag 自动推导出的版本 |
| `publish`            | 是否推送                                                                              |
| `image_repositories` | 发布目标仓库                                                                          |

该 workflow 会先生成匹配 tag 和 `image_key` 列表，再逐个调用 `Build and Publish Image`。同一 `image_version` 下的不同分类会分别发布到自己的仓库后缀。

## 6. 发布凭据

默认 GHCR 发布使用 `GITHUB_TOKEN`，需要 workflow 具备 `packages: write` 权限。发布到其他仓库时配置以下 Secrets：

| 目标             | Secrets                                                                         |
| ---------------- | ------------------------------------------------------------------------------- |
| DockerHub        | `DOCKER_USERNAME`, `DOCKER_TOKEN`                                               |
| Quay.io          | `QUAY_USERNAME`, `QUAY_TOKEN`                                                   |
| Huawei Cloud SWR | `SWR_USERNAME`, `SWR_PASSWORD`；也兼容 `SWR_TOKEN` 或 `HW_USERNAME`, `HW_TOKEN` |

## 7. 常见问题

### runner 不存在或架构不匹配

检查 `image_publish_version.json` 中 `arches[].runner` 是否与仓库可用 runner 名称一致。某些运行环境只适合 `linux/amd64`，应显式配置 `arches` 或依赖工具的默认推导。

### 发布到 DockerHub、Quay 或 Huawei Cloud SWR 登录失败

确认 `image_repositories` 中包含的 registry 与 Secrets 匹配。例如发布到 `docker.io/<namespace>` 时必须配置 `DOCKER_USERNAME` 和 `DOCKER_TOKEN`；发布到 `swr.cn-southwest-2.myhuaweicloud.com/<organization>` 时必须配置 SWR 对应凭据。

### 需要新增别名 tag

在对应版本的 `tags` 数组中追加别名即可。发布 workflow 会为每个仓库生成所有 tag 的 manifest list。
