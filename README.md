
## Example

I've created multiple steps' scripts and put them under the step folder.
These scripts will show you how to extend it and integrate it into the Jenkins.

### Snapshot

![image](readme.assets/jenkins_snapshot.png)

### Script in Jenkins

```bash
set -Ee
set +x

# if this server restarted, the following line can be removed.
# source /etc/profile

# devops script address and configuration file.
DEVOPS_SCRIPT_URL="http://192.168.1.2:3000/devops/devops-scripts/archive/develop.tar.gz"
DEVOPS_CONFIG_URL="http://192.168.1.2:3000/devops/devops-confs/raw/develop/jenkins/xxx-services.yaml"

# default parameters
PARAM_DINGDING_TOKEN="xxxxxxx"
PARAM_SONAR_HOST="http://192.168.1.2:9000"
PARAM_SONAR_AUTH_TOKEN="xxxxxx"
PARAM_BUILD_ICON_FAIL="http://192.168.1.2:8099/jenkins/static/20cbeeb5/images/48x48/red.png"

# given parameters (提取环境变量)
ENV="-e build_display_name="${BUILD_DISPLAY_NAME}" -e dingding_token=${PARAM_DINGDING_TOKEN} -e build_icon_fail=${PARAM_BUILD_ICON_FAIL} -e build_url=${BUILD_URL}"
[[ -n ${PARAM_REPOSITORY} ]] && ENV="${ENV} -e repository=${PARAM_REPOSITORY}"
[[ -n ${PARAM_SONAR_HOST} ]] && ENV="${ENV} -e sonar_url=${PARAM_SONAR_HOST}"
[[ -n ${PARAM_SONAR_AUTH_TOKEN} ]] && ENV="${ENV} -e sonar_auth_token=${PARAM_SONAR_AUTH_TOKEN}"
[[ -n ${PARAM_SKIP_UNIT_TEST} ]] && ENV="${ENV} -e skip_unit_test=${PARAM_SKIP_UNIT_TEST}"
[[ -n ${PARAM_SKIP_IT_TEST} ]] && ENV="${ENV} -e skip_it_test=${PARAM_SKIP_IT_TEST}"
[[ -n ${PARAM_RELEASE_VERSION} ]] && ENV="${ENV} -e release_version=${PARAM_RELEASE_VERSION} -e hotfix_version=${PARAM_RELEASE_VERSION}"
[[ -n ${PARAM_RELEASE_COMMENT} ]] && ENV="${ENV} -e release_comment=\"$(sed "s/\"/\\\\\"/g" <<< ${PARAM_RELEASE_COMMENT})\""
[[ -n ${PARAM_RELEASE_VERSION_TAG} ]] && ENV="${ENV} -e release_tag=${PARAM_RELEASE_VERSION_TAG}"
[[ -n ${PARAM_NEXT_DEVELOP_VERSION} ]] && ENV="${ENV} -e next_develop_version=${PARAM_NEXT_DEVELOP_VERSION}"
[[ -n ${PARAM_MERGE_INTO} ]] && ENV="${ENV} -e merge_into=${PARAM_MERGE_INTO}"
[[ -n ${PARAM_DEPLOY_COMMIT} ]] && ENV="${ENV} -e deploy_commit=${PARAM_DEPLOY_COMMIT}"
[[ -n ${PARAM_REGISTRIES} ]] && ENV="${ENV} -e registries=${PARAM_REGISTRIES}"
[[ -n ${PARAM_SERVERS} ]] && ENV="${ENV} -e servers=${PARAM_SERVERS}"

if [[ -n $PARAM_ENV ]]; then
    ENV=${ENV} $(
python3 << EOF
import re

combined = " ".join([f"-e {key}={value}" for key, value in re.findall(r'\s*([^= ]+)=(".*?(?<!\\\\)"|[^" ]*)', '${PARAM_ENV}')])
print(combined)
EOF
)
fi

# Python 可执行文件
export PYTHON_EXECUTABLE=python3

# 直接从git仓库中下载最新的脚本
pip3 install -U ${DEVOPS_SCRIPT_URL} -i https://mirrors.aliyun.com/pypi/simple

# 执行脚本，并附带参数
cmd="${PYTHON_EXECUTABLE} -m jobchain -f ${DEVOPS_CONFIG_URL} -r xxx-services -j ${PARAM_JOB} --maven-executor \"/home/maven/bin/mvn {}\" ${ENV}"

echo "the command is: ${cmd}"
eval ${cmd}
```
