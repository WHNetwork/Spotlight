import QtQuick
import QtQuick.Controls
import "../components"

Item {
    id: settingsPage
    signal backRequested()

    readonly property real sp: Math.max(0.72, Math.min(1.12, Math.min(width / 1536.0, height / 864.0)))

    // Form state. Field values are initialized once from the controller and
    // then edited in place (read back at save time) to avoid bidirectional
    // binding fights. API key fields stay empty on purpose.
    property string selProvider: settingsController.provider
    property string selPolicy: settingsController.modelPolicy

    // --- background (existing static functional page bg, unchanged path) ---
    Image {
        anchors.fill: parent
        source: assetBridge.assetUrl("backgrounds/subpage_bg.png")
        fillMode: Image.PreserveAspectCrop
    }
    Rectangle {
        anchors.fill: parent
        color: "#FFFFFF"
        opacity: 0.06
    }

    // --- header ---
    Item {
        id: header
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 42 * sp
        anchors.rightMargin: 42 * sp
        anchors.topMargin: 28 * sp
        height: 56 * sp

        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            spacing: 12 * sp
            Item {
                width: 44 * sp
                height: 44 * sp
                anchors.verticalCenter: parent.verticalCenter
                Rectangle { anchors.fill: parent; radius: width / 2; color: Qt.rgba(0.97, 0.93, 0.94, 0.45) }
                Image {
                    anchors.centerIn: parent
                    source: assetBridge.iconUrl("settings")
                    width: 26 * sp; height: 26 * sp
                    fillMode: Image.PreserveAspectFit
                    sourceSize: Qt.size(28 * sp, 28 * sp)
                }
            }
            Column {
                spacing: 1
                anchors.verticalCenter: parent.verticalCenter
                Text { text: "系统设置"; color: "#3D4963"; font.pixelSize: 22 * sp; font.bold: true; font.family: "Microsoft YaHei UI" }
                Text { text: "模型服务商、API Key 与生成模型配置"; color: "#7B8498"; font.pixelSize: 12 * sp; font.family: "Microsoft YaHei UI" }
            }
        }

        GlassAction {
            id: backBtn
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            scaleFactor: sp
            label: "返回首页"
            iconSource: assetBridge.iconUrl("app_logo")
            onClicked: settingsPage.backRequested()
        }
    }

    // --- scrollable body ---
    Flickable {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.topMargin: 10 * sp
        anchors.bottomMargin: 10 * sp
        contentWidth: width
        contentHeight: bodyCol.implicitHeight + 24 * sp
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: bodyCol
            width: Math.min(parent.width - 84 * sp, 960 * sp)
            x: (parent.width - width) / 2
            spacing: 22 * sp

            // ===== strategy panel =====
            GlassPanel {
                id: strategyPanel
                width: parent.width
                height: strategyCol.implicitHeight + 2 * strategyPanel.padding
                scaleFactor: settingsPage.sp
                radius: 20 * settingsPage.sp
                glassAlpha: 0.30
                shadowAlpha: 0.05

                Column {
                    id: strategyCol
                    anchors.fill: parent
                    spacing: 16 * sp

                    Text { text: "生成策略"; color: "#3D4963"; font.pixelSize: 15 * sp; font.bold: true; font.family: "Microsoft YaHei UI" }

                    Text { text: "服务商"; color: "#68738C"; font.pixelSize: 11 * sp; font.family: "Microsoft YaHei UI" }
                    SegmentedControl {
                        width: parent.width
                        scaleFactor: settingsPage.sp
                        currentValue: settingsPage.selProvider
                        items: [
                            { value: "deepseek", label: "DeepSeek" },
                            { value: "mimo", label: "Xiaomi MiMo" },
                            { value: "glm", label: "GLM" }
                        ]
                        onValueSelected: function(value) {
                            settingsPage.selProvider = value
                        }
                    }

                    Text { text: "模型档位"; color: "#68738C"; font.pixelSize: 11 * sp; font.family: "Microsoft YaHei UI" }
                    SegmentedControl {
                        width: parent.width
                        scaleFactor: settingsPage.sp
                        currentValue: settingsPage.selPolicy
                        items: [
                            { value: "flash", label: "Flash" },
                            { value: "pro", label: "Pro" },
                            { value: "custom", label: "Custom" }
                        ]
                        onValueSelected: function(value) {
                            settingsPage.selPolicy = value
                        }
                    }

                    GlassInput {
                        id: timeoutInput
                        width: parent.width
                        scaleFactor: settingsPage.sp
                        label: "超时时间（秒）"
                        Component.onCompleted: text = String(settingsController.timeoutSeconds)
                    }
                }
            }

            // ===== current provider config panel =====
            GlassPanel {
                id: providerPanel
                width: parent.width
                height: providerCol.implicitHeight + 2 * providerPanel.padding
                scaleFactor: settingsPage.sp
                radius: 20 * settingsPage.sp
                glassAlpha: 0.30
                shadowAlpha: 0.05

                Column {
                    id: providerCol
                    anchors.fill: parent
                    spacing: 14 * sp

                    Text { text: "当前服务商配置"; color: "#3D4963"; font.pixelSize: 15 * sp; font.bold: true; font.family: "Microsoft YaHei UI" }
                    Text { text: "API Key 优先存入系统密钥环，失败时保存到用户配置目录；留空则保持已有 Key 不变。"; color: "#7B8498"; font.pixelSize: 11 * sp; font.family: "Microsoft YaHei UI"; wrapMode: Text.WordWrap; width: parent.width }

                    // ----- DeepSeek fields -----
                    Column {
                        width: parent.width
                        visible: settingsPage.selProvider === "deepseek"
                        spacing: 12 * sp
                        GlassInput { id: dsKey; width: parent.width; scaleFactor: settingsPage.sp; label: "DeepSeek API Key"; password: true; revealable: true; placeholder: settingsController.deepSeekKeyHint }
                        GlassInput { id: dsBaseUrl; width: parent.width; scaleFactor: settingsPage.sp; label: "Base URL"; Component.onCompleted: text = settingsController.deepseekBaseUrl }
                        GlassInput { id: dsFlash; width: parent.width; scaleFactor: settingsPage.sp; label: "Flash Model"; Component.onCompleted: text = settingsController.deepseekFlashModel }
                        GlassInput { id: dsPro; width: parent.width; scaleFactor: settingsPage.sp; label: "Pro Model"; Component.onCompleted: text = settingsController.deepseekProModel }
                        GlassInput { id: dsCustom; width: parent.width; scaleFactor: settingsPage.sp; label: "Custom Model"; Component.onCompleted: text = settingsController.deepseekCustomModel }
                    }

                    // ----- MiMo fields -----
                    Column {
                        width: parent.width
                        visible: settingsPage.selProvider === "mimo"
                        spacing: 12 * sp
                        GlassInput { id: mimoKey; width: parent.width; scaleFactor: settingsPage.sp; label: "Xiaomi MiMo API Key"; password: true; revealable: true; placeholder: settingsController.mimoKeyHint }
                        GlassInput { id: mimoBaseUrl; width: parent.width; scaleFactor: settingsPage.sp; label: "Base URL"; Component.onCompleted: text = settingsController.mimoBaseUrl }
                        GlassInput { id: mimoFlash; width: parent.width; scaleFactor: settingsPage.sp; label: "Flash Model"; Component.onCompleted: text = settingsController.mimoFlashModel }
                        GlassInput { id: mimoPro; width: parent.width; scaleFactor: settingsPage.sp; label: "Pro Model"; Component.onCompleted: text = settingsController.mimoProModel }
                        GlassInput { id: mimoCustom; width: parent.width; scaleFactor: settingsPage.sp; label: "Custom Model"; Component.onCompleted: text = settingsController.mimoCustomModel }
                    }

                    // ----- GLM fields -----
                    Column {
                        width: parent.width
                        visible: settingsPage.selProvider === "glm"
                        spacing: 12 * sp
                        GlassInput { id: glmKey; width: parent.width; scaleFactor: settingsPage.sp; label: "GLM API Key"; password: true; revealable: true; placeholder: settingsController.glmKeyHint }
                        GlassInput { id: glmBaseUrl; width: parent.width; scaleFactor: settingsPage.sp; label: "Base URL"; Component.onCompleted: text = settingsController.glmBaseUrl }
                        GlassInput { id: glmFlash; width: parent.width; scaleFactor: settingsPage.sp; label: "Flash Model"; Component.onCompleted: text = settingsController.glmFlashModel }
                        GlassInput { id: glmPro; width: parent.width; scaleFactor: settingsPage.sp; label: "Pro Model"; Component.onCompleted: text = settingsController.glmProModel }
                        GlassInput { id: glmCustom; width: parent.width; scaleFactor: settingsPage.sp; label: "Custom Model"; Component.onCompleted: text = settingsController.glmCustomModel }
                    }
                }
            }

            // ===== action row + status =====
            Column {
                width: parent.width
                spacing: 10 * sp

                Row {
                    width: parent.width
                    spacing: 14 * sp
                    layoutDirection: Qt.RightToLeft

                    GlassAction {
                        id: saveBtn
                        scaleFactor: settingsPage.sp
                        label: "保存设置"
                        iconSource: assetBridge.iconUrl("save_archive")
                        primary: true
                        onClicked: saveAll()
                    }
                    GlassAction {
                        id: testBtn
                        scaleFactor: settingsPage.sp
                        label: settingsController.testing ? "正在测试…" : "测试当前模型"
                        iconSource: assetBridge.iconUrl("api")
                        enabled: !settingsController.testing
                        onClicked: settingsController.testCurrentModel(collectFormValues())
                    }
                }

                // Fixed-min-height status area: success / loading are short
                // one-liners (no jump); errors may wrap and grow. Color:
                // testing = purple-gray, success = mint, error = coral.
                Item {
                    width: parent.width
                    height: Math.max(30 * sp, statusText.implicitHeight)

                    Text {
                        id: statusText
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: settingsController.statusText
                        color: settingsController.testing
                               ? "#7A7F9C"
                               : (settingsController.statusIsError
                                  ? "#D86B7A"
                                  : (settingsController.statusText.indexOf("连接成功") >= 0
                                     ? "#7FAE9A"
                                     : "#6A6684"))
                        font.pixelSize: 12 * settingsPage.sp
                        font.family: "Microsoft YaHei UI"
                        wrapMode: Text.WordWrap
                        opacity: settingsController.statusText !== "" ? 1.0 : 0.0
                        Behavior on opacity { NumberAnimation { duration: 140 } }
                    }
                }
            }
        }
    }

    function collectFormValues() {
        return {
            provider: selProvider,
            policy: selPolicy,
            timeout: timeoutInput.text,
            deepseekBaseUrl: dsBaseUrl.text,
            deepseekFlashModel: dsFlash.text,
            deepseekProModel: dsPro.text,
            deepseekCustomModel: dsCustom.text,
            mimoBaseUrl: mimoBaseUrl.text,
            mimoFlashModel: mimoFlash.text,
            mimoProModel: mimoPro.text,
            mimoCustomModel: mimoCustom.text,
            glmBaseUrl: glmBaseUrl.text,
            glmFlashModel: glmFlash.text,
            glmProModel: glmPro.text,
            glmCustomModel: glmCustom.text,
            deepseekApiKey: dsKey.text,
            mimoApiKey: mimoKey.text,
            glmApiKey: glmKey.text,
        }
    }

    function saveAll() {
        settingsController.saveSettings(collectFormValues())
    }

    Component.onCompleted: {
        selProvider = settingsController.provider
        selPolicy = settingsController.modelPolicy
    }
}
