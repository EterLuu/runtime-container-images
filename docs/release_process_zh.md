# ModelArts 镜像发布流程

本文档说明如何维护和发布 `modelarts/*` 下的 ModelArts 适配镜像。整体流程参考 `cann-container-image`：先在 PR 中完成构建验证，合并后通过手动 workflow 发布镜像。

## 1. 版本和标签规范

推荐标签格式：

```text
<cann-version>-<chip>-<os><os-version>
```

当前模板示例：

```text
9.0.0-910b-ubuntu22.04
```

该标签表示镜像基于 `ascendai/cann:9.0.0-910b-ubuntu22.04-py3.11`，适配 Ascend 910B，操作系统为 Ubuntu 22.04。
当前模板会自动衍生以下 tag：

```text
9.0.0-310p-ubuntu22.04
9.0.0-910-ubuntu22.04
9.0.0-950-ubuntu22.04
9.0.0-a3-ubuntu22.04
```

衍生过程只替换 Dockerfile 顶层 `BASE_IMAGE`，例如把 `ascendai/cann:9.0.0-910b-ubuntu22.04-py3.11` 替换为 `ascendai/cann:9.0.0-310p-ubuntu22.04-py3.11`。
构建前会自动把 `modelarts/scripts` 复制到目标构建目录的 `scripts/` 下，供 Dockerfile 中的 `COPY scripts/...` 使用。

## 2. 新增或更新镜像

1. 在 `modelarts/<tag>/Dockerfile` 新增或修改 Dockerfile。
2. 更新 `modelarts_publish_version.json`：
   - `path` 指向 Dockerfile 所在目录。
   - `tags` 写入要发布的 tag 列表。
   - `chip` 写模板芯片，例如 `910b`。
   - `derived_chips` 写可由模板衍生的芯片，例如 `["310p", "910", "950", "a3"]`。
   - `base_image` 写模板基础镜像，衍生芯片会自动替换其中的芯片字段。
   - `modelarts_version` 用于批量发布筛选。
   - `arches` 定义目标平台和 GitHub Actions runner。
3. 如果需要更新容器启动或 SSH 逻辑，修改 `modelarts/scripts`，不要提交生成到 `modelarts/<tag>/scripts` 下的副本。
4. 本地执行校验：

```bash
python3 scripts/modelarts_metadata.py validate
```

5. 可选，本地构建验证：

```bash
IMAGE_REPOSITORY=modelarts-cann \
  scripts/build_modelarts.sh 9.0.0-310p-ubuntu22.04
```

## 3. PR 构建验证

提交 PR 后，`Build ModelArts Image` 会自动运行：

- 校验 `modelarts_publish_version.json`。
- 为每个展开后的镜像 tag 和目标平台生成 matrix。
- 使用 `docker/build-push-action` 构建镜像，但不推送。

如果没有可用的 ARM runner，可以临时在 `modelarts_publish_version.json` 中移除 `linux/arm64` 对应的 `arches` 项，或将 `runner` 改为仓库可用的自托管 runner。

## 4. 发布单个镜像

在 GitHub Actions 页面手动运行 `Build and Publish ModelArts Image`：

| 参数                 | 说明                                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------------ |
| `modelarts_tag`      | `modelarts_publish_version.json` 中定义的 tag                                                    |
| `publish`            | `true` 时推送镜像；`false` 时只构建                                                              |
| `image_repositories` | 发布目标仓库，留空时使用仓库变量 `IMAGE_REPOSITORIES`，再回退到 `ghcr.io/<owner>/modelarts-cann` |

发布到多个仓库时使用逗号或空白分隔：

```text
ghcr.io/<owner>/modelarts-cann,docker.io/<namespace>/modelarts-cann,quay.io/<namespace>/modelarts-cann,swr.cn-southwest-2.myhuaweicloud.com/<organization>/modelarts-cann
```

仓库名会自动转换为小写；例如 `ghcr.io/EterLuu/modelarts-cann` 会规范化为 `ghcr.io/eterluu/modelarts-cann`。

可以在 `Settings -> Secrets and variables -> Actions -> Variables` 中添加仓库变量：

```text
IMAGE_REPOSITORIES=swr.cn-southwest-2.myhuaweicloud.com/<organization>/modelarts-cann
```

手动运行 workflow 时，`image_repositories` 输入为空会自动使用该变量；填写输入值则覆盖该变量。
`IMAGE_REPOSITORIES` 和 `image_repositories` 只能包含镜像仓库地址，不要写入用户名、密码、token 或 URL scheme。登录凭据必须放在 Secrets 中。

发布流程会先按架构推送 digest，再创建并推送最终 manifest list，因此最终 tag 是多架构镜像。

## 5. 批量发布

运行 `Batch Build and Publish ModelArts Image`：

| 参数                 | 说明                                                           |
| -------------------- | -------------------------------------------------------------- |
| `modelarts_version`  | 匹配 `modelarts_publish_version.json` 中的 `modelarts_version` |
| `publish`            | 是否推送                                                       |
| `image_repositories` | 发布目标仓库                                                   |

该 workflow 会先生成匹配 tag 列表，再逐个调用 `Build and Publish ModelArts Image`。

## 6. 发布凭据

默认 GHCR 发布使用 `GITHUB_TOKEN`，需要 workflow 具备 `packages: write` 权限。发布到其他仓库时配置以下 Secrets：

| 目标             | Secrets                                                                         |
| ---------------- | ------------------------------------------------------------------------------- |
| DockerHub        | `DOCKER_USERNAME`, `DOCKER_TOKEN`                                               |
| Quay.io          | `QUAY_USERNAME`, `QUAY_TOKEN`                                                   |
| Huawei Cloud SWR | `SWR_USERNAME`, `SWR_PASSWORD`；也兼容 `SWR_TOKEN` 或 `HW_USERNAME`, `HW_TOKEN` |

## 7. 常见问题

### ARM 构建失败或 runner 不存在

检查 `modelarts_publish_version.json` 中 `arches[].runner` 是否与仓库可用 runner 名称一致。GitHub 托管 ARM runner 不可用时，可以改成自托管 runner label。

### 发布到 DockerHub、Quay 或 Huawei Cloud SWR 登录失败

确认 `image_repositories` 中包含的 registry 与 Secrets 匹配。例如发布到 `docker.io/<namespace>/modelarts-cann` 时必须配置 `DOCKER_USERNAME` 和 `DOCKER_TOKEN`；发布到 `swr.cn-southwest-2.myhuaweicloud.com/<organization>/modelarts-cann` 时必须配置 SWR 对应凭据。

### 需要新增别名 tag

在对应版本的 `tags` 数组中追加别名即可。发布 workflow 会为每个仓库生成所有 tag 的 manifest list。
