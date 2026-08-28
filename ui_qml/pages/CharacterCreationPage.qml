import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import "../components"

Item {
    id: charPage
    signal backRequested()

    readonly property real sp: Math.max(0.72, Math.min(1.12, Math.min(width / 1536.0, height / 864.0)))
    readonly property bool wide: width >= 900

    // Form state (basic + start point).
    property string selIdentity: "素人学生被星探发现"
    property string selCompanySize: "中型公司"
    property string selEducation: "ENROLLED"
    property bool aiReady: characterController.aiReady
    property var aiResult: ({})
    property var aiTags: []

    // Opening message dialog (LLM-generated, shown on page entry).
    property bool openingVisible: false
    property bool openingLoading: false
    property bool openingFallbackUsed: false
    property string openingText: ""

    // --- background (existing static functional page bg, unchanged path) ---
    Image {
        id: bgImage
        anchors.fill: parent
        source: assetBridge.assetUrl("backgrounds/character_create_office_bg.png")
        fillMode: Image.PreserveAspectCrop
    }
    Rectangle {
        anchors.fill: parent
        color: "#FFFFFF"
        opacity: 0.06
    }

    // --- shared frosted-glass source (HomePage 同一套实现) ----------------
    // ONE blur of the page background, masked to the three content Panel
    // footprints. The mask follows the Flickable scroll via plain QML
    // bindings (no Timer, no Python per-frame). Blur is only visible inside
    // the panels, so the crisp background stays visible elsewhere.
    Item {
        id: glassMask
        anchors.fill: parent
        visible: false

        Rectangle {
            x: bodyCol.x + basicPanel.x
            y: flick.y + basicPanel.y - flick.contentY
            width: basicPanel.width
            height: basicPanel.height
            radius: basicPanel.radius
            color: "#FFFFFF"
        }
        Rectangle {
            x: bodyCol.x + startPanel.x
            y: flick.y + startPanel.y - flick.contentY
            width: startPanel.width
            height: startPanel.height
            radius: startPanel.radius
            color: "#FFFFFF"
        }
        Rectangle {
            visible: aiPanel.visible
            x: bodyCol.x + aiPanel.x
            y: flick.y + aiPanel.y - flick.contentY
            width: aiPanel.width
            height: aiPanel.height
            radius: aiPanel.radius
            color: "#FFFFFF"
        }
    }

    MultiEffect {
        id: sharedBlur
        anchors.fill: parent
        source: bgImage
        blurEnabled: true
        blur: 0.6
        blurMax: 32
        maskEnabled: true
        maskSource: glassMask
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
                width: 44 * sp; height: 44 * sp
                anchors.verticalCenter: parent.verticalCenter
                Rectangle { anchors.fill: parent; radius: width / 2; color: Qt.rgba(0.97, 0.93, 0.94, 0.45) }
                Image {
                    anchors.centerIn: parent
                    source: assetBridge.iconUrl("new_character")
                    width: 26 * sp; height: 26 * sp
                    fillMode: Image.PreserveAspectFit
                    sourceSize: Qt.size(28 * sp, 28 * sp)
                }
            }
            Column {
                spacing: 1
                anchors.verticalCenter: parent.verticalCenter
                Text { text: "角色创建"; color: "#3D4963"; font.pixelSize: 22 * sp; font.bold: true; font.family: "Microsoft YaHei UI" }
                Text { text: "基础数据确认后自动校验并生成 AI 设定；生成结果可以微调。"; color: "#7B8498"; font.pixelSize: 12 * sp; font.family: "Microsoft YaHei UI" }
            }
        }

        GlassAction {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            scaleFactor: charPage.sp
            label: "返回首页"
            iconSource: assetBridge.iconUrl("app_logo")
            onClicked: charPage.backRequested()
        }
    }

    // --- scrollable body ---
    Flickable {
        id: flick
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
            width: Math.min(parent.width - 84 * sp, 1000 * sp)
            x: (parent.width - width) / 2
            spacing: 22 * sp

            // ===== 1. 基本资料 =====
            GlassPanel {
                id: basicPanel
                width: parent.width
                height: basicCol.implicitHeight + 2 * basicPanel.padding
                scaleFactor: charPage.sp
                radius: 20 * charPage.sp
                glassAlpha: 0.55
                tintColor: Qt.rgba(0.86, 0.82, 0.97, 0.10)
                shadowAlpha: 0.05

                Column {
                    id: basicCol
                    anchors.fill: parent
                    spacing: 14 * sp

                    Text { text: "基本资料"; color: "#3D4963"; font.pixelSize: 15 * sp; font.bold: true; font.family: "Microsoft YaHei UI" }
                    Text { text: "决定角色最基础的个人信息。"; color: "#7B8498"; font.pixelSize: 11 * sp; font.family: "Microsoft YaHei UI" }

                    Grid {
                        id: basicGrid
                        width: parent.width
                        columns: charPage.wide ? 2 : 1
                        columnSpacing: 14 * sp
                        rowSpacing: 12 * sp

                        readonly property real cellW: (basicGrid.width - (columns - 1) * basicGrid.columnSpacing) / columns

                        GlassInput { id: realNameInput; width: basicGrid.cellW; scaleFactor: charPage.sp; label: "本名" }
                        GlassInput { id: stageNameInput; width: basicGrid.cellW; scaleFactor: charPage.sp; label: "艺名" }
                        GlassInput { id: ageInput; width: basicGrid.cellW; scaleFactor: charPage.sp; label: "年龄" }
                        GlassInput { id: heightInput; width: basicGrid.cellW; scaleFactor: charPage.sp; label: "身高"; unit: "cm" }
                        GlassDropdown {
                            id: nationalityDrop
                            width: basicGrid.cellW
                            scaleFactor: charPage.sp
                            label: "国籍"
                            options: characterController.nationalityOptions
                            Component.onCompleted: value = "中国"
                        }
                        GlassDropdown {
                            id: mbtiDrop
                            width: basicGrid.cellW
                            scaleFactor: charPage.sp
                            label: "MBTI"
                            options: characterController.mbtiOptions
                            Component.onCompleted: value = "INFP"
                        }
                    }

                    Text { text: "是否在学"; color: "#68738C"; font.pixelSize: 11 * sp; font.family: "Microsoft YaHei UI" }
                    SegmentedControl {
                        width: parent.width
                        scaleFactor: charPage.sp
                        currentValue: charPage.selEducation
                        items: [
                            { value: "ENROLLED", label: "在学" },
                            { value: "NOT_ENROLLED", label: "已离校" }
                        ]
                        onValueSelected: function(value) {
                            charPage.selEducation = value
                        }
                    }
                }
            }

            // ===== 2. 练习生起点 =====
            GlassPanel {
                id: startPanel
                width: parent.width
                height: startCol.implicitHeight + 2 * startPanel.padding
                scaleFactor: charPage.sp
                radius: 20 * charPage.sp
                glassAlpha: 0.55
                tintColor: Qt.rgba(0.86, 0.82, 0.97, 0.10)
                shadowAlpha: 0.05

                Column {
                    id: startCol
                    anchors.fill: parent
                    spacing: 14 * sp

                    Text { text: "练习生起点"; color: "#3D4963"; font.pixelSize: 15 * sp; font.bold: true; font.family: "Microsoft YaHei UI" }
                    Text { text: "决定你以怎样的身份进入当前公司。"; color: "#7B8498"; font.pixelSize: 11 * sp; font.family: "Microsoft YaHei UI" }

                    Grid {
                        id: startGrid
                        width: parent.width
                        columns: charPage.wide ? 2 : 1
                        columnSpacing: 14 * sp
                        rowSpacing: 12 * sp

                        readonly property real cellW: (startGrid.width - (columns - 1) * startGrid.columnSpacing) / columns

                        GlassDropdown {
                            id: identityDrop
                            width: startGrid.cellW
                            scaleFactor: charPage.sp
                            label: "身份来源"
                            options: characterController.identityOptions
                            onValueSelected: charPage.selIdentity = value
                            Component.onCompleted: value = charPage.selIdentity
                        }
                        Column {
                            width: startGrid.cellW
                            spacing: 4 * charPage.sp
                            Text { text: "公司规模"; color: "#68738C"; font.pixelSize: 11 * sp; font.family: "Microsoft YaHei UI" }
                            SegmentedControl {
                                width: parent.width
                                scaleFactor: charPage.sp
                                currentValue: charPage.selCompanySize
                                items: [
                                    { value: "大型公司", label: "大型" },
                                    { value: "中型公司", label: "中型" },
                                    { value: "小型公司", label: "小型" }
                                ]
                                onValueSelected: function(value) {
                                    charPage.selCompanySize = value
                                }
                            }
                        }
                    }

                    // Actions
                    Row {
                        width: parent.width
                        spacing: 14 * sp
                        layoutDirection: Qt.RightToLeft

                        GlassAction {
                            id: confirmBtn
                            scaleFactor: charPage.sp
                            label: characterController.generating ? "正在生成…" : "确认并生成角色设定"
                            iconSource: assetBridge.iconUrl("api")
                            primary: true
                            enabled: !characterController.generating
                            onClicked: generateAI()
                        }
                        GlassAction {
                            id: randomBtn
                            scaleFactor: charPage.sp
                            label: "随机生成基础资料"
                            iconSource: assetBridge.iconUrl("dice")
                            enabled: !characterController.generating
                            onClicked: applyRandom()
                        }
                    }
                }
            }

            // ===== status area (fixed min height, no layout jump) =====
            Item {
                width: parent.width
                height: Math.max(30 * sp, charStatusText.implicitHeight)
                Text {
                    id: charStatusText
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    text: charStatusTextContent
                    color: statusIsError ? "#D86B7A" : "#7A7F9C"
                    font.pixelSize: 12 * charPage.sp
                    font.family: "Microsoft YaHei UI"
                    wrapMode: Text.WordWrap
                    opacity: charStatusTextContent !== "" ? 1.0 : 0.0
                    Behavior on opacity { NumberAnimation { duration: 140 } }
                }
            }

            // ===== 3. AI 角色设定 (only after generation) =====
            GlassPanel {
                id: aiPanel
                width: parent.width
                height: aiCol.implicitHeight + 2 * aiPanel.padding
                scaleFactor: charPage.sp
                radius: 20 * charPage.sp
                glassAlpha: 0.55
                tintColor: Qt.rgba(0.86, 0.82, 0.97, 0.10)
                shadowAlpha: 0.05
                visible: charPage.aiReady

                Column {
                    id: aiCol
                    anchors.fill: parent
                    spacing: 14 * sp

                    Text { text: "AI 角色设定"; color: "#3D4963"; font.pixelSize: 15 * sp; font.bold: true; font.family: "Microsoft YaHei UI" }
                    Text { text: "生成结果可以直接微调，然后开始练习生生涯。"; color: "#7B8498"; font.pixelSize: 11 * sp; font.family: "Microsoft YaHei UI" }

                    Grid {
                        id: aiGrid
                        width: parent.width
                        columns: charPage.wide ? 2 : 1
                        columnSpacing: 14 * sp
                        rowSpacing: 12 * sp

                        readonly property real cellW: (aiGrid.width - (columns - 1) * aiGrid.columnSpacing) / columns

                        GlassInput { id: aiPersonality; width: aiGrid.cellW; scaleFactor: charPage.sp; label: "性格"; multiline: true }
                        GlassInput { id: aiAppearance; width: aiGrid.cellW; scaleFactor: charPage.sp; label: "外貌风格"; multiline: true }
                        GlassInput { id: aiInterests; width: aiGrid.cellW; scaleFactor: charPage.sp; label: "爱好"; multiline: true }
                        GlassInput { id: aiStrengths; width: aiGrid.cellW; scaleFactor: charPage.sp; label: "特长"; multiline: true }
                        GlassInput { id: aiWeaknesses; width: aiGrid.cellW; scaleFactor: charPage.sp; label: "弱项"; multiline: true }
                        GlassInput { id: aiPosition; width: aiGrid.cellW; scaleFactor: charPage.sp; label: "在团定位"; multiline: true }
                        GlassInput { id: aiFamily; width: aiGrid.cellW; scaleFactor: charPage.sp; label: "家庭状况"; multiline: true }
                        GlassInput { id: aiBackground; width: aiGrid.cellW; scaleFactor: charPage.sp; label: "练习生经历"; multiline: true }
                        GlassInput { id: aiWish; width: aiGrid.cellW; scaleFactor: charPage.sp; label: "你希望观众记住你的什么"; multiline: true }
                        GlassInput { id: aiExtra; width: aiGrid.cellW; scaleFactor: charPage.sp; label: "其他补充"; multiline: true }
                    }

                    GlassInput {
                        id: aiBoundary
                        width: parent.width
                        scaleFactor: charPage.sp
                        label: "剧情边界（你不希望触碰的内容）"
                        placeholder: "由你填写，例如：不写极端暴力、强制亲密、未成年露骨恋爱等"
                        multiline: true
                    }

                    Flow {
                        width: parent.width
                        spacing: 6 * sp
                        Text { text: "出身来源标签："; color: "#68738C"; font.pixelSize: 12 * sp; font.family: "Microsoft YaHei UI"; anchors.verticalCenter: parent.verticalCenter }
                        Repeater {
                            model: charPage.aiTags
                            Rectangle {
                                width: tagText.implicitWidth + 14 * sp
                                height: 24 * sp
                                radius: 8 * sp
                                color: Qt.rgba(0.93, 0.9, 0.97, 0.5)
                                Text {
                                    id: tagText
                                    anchors.centerIn: parent
                                    text: modelData
                                    color: "#5A6480"
                                    font.pixelSize: 11 * sp
                                    font.family: "Microsoft YaHei UI"
                                }
                            }
                        }
                    }

                    Row {
                        width: parent.width
                        spacing: 14 * sp
                        layoutDirection: Qt.RightToLeft

                        GlassAction {
                            id: createBtn
                            scaleFactor: charPage.sp
                            label: "开始练习生生涯"
                            iconSource: assetBridge.iconUrl("app_logo")
                            primary: true
                            onClicked: createCharacter()
                        }
                        GlassAction {
                            id: regenBtn
                            scaleFactor: charPage.sp
                            label: "重新生成"
                            iconSource: assetBridge.iconUrl("api")
                            enabled: !characterController.generating
                            onClicked: generateAI()
                        }
                    }
                }
            }
        }
    }

    // ---- page logic -------------------------------------------------------
    property string charStatusTextContent: ""
    property bool statusIsError: false

    function setStatus(text, isError) {
        charStatusTextContent = text
        statusIsError = isError
    }

    function applyRandom() {
        var r = characterController.randomizeBasic({国籍: nationalityDrop.value})
        nationalityDrop.value = r["国籍"]
        realNameInput.text = r["本名"]
        stageNameInput.text = r["艺名"]
        ageInput.text = r["年龄"]
        heightInput.text = r["身高"]
        mbtiDrop.value = r["MBTI"]
        setStatus("已随机生成基础资料。", false)
    }

    function collectBasic() {
        return {
            身份: charPage.selIdentity,
            公司规模: charPage.selCompanySize,
            国籍: nationalityDrop.value,
            MBTI: mbtiDrop.value,
            艺名: stageNameInput.text,
            本名: realNameInput.text,
            年龄: ageInput.text,
            身高: heightInput.text
        }
    }

    function generateAI() {
        setStatus("正在生成角色设定…", false)
        characterController.generateCharacterMatch(collectBasic())
    }

    function createCharacter() {
        var msg = characterController.createCharacter({
            identity: charPage.selIdentity,
            companySize: charPage.selCompanySize,
            nationality: nationalityDrop.value,
            mbti: mbtiDrop.value,
            educationStatus: charPage.selEducation,
            stageName: stageNameInput.text,
            realName: realNameInput.text,
            age: ageInput.text,
            height: heightInput.text,
            appearance: aiAppearance.text,
            personality: aiPersonality.text,
            interests: aiInterests.text,
            strengths: aiStrengths.text,
            weaknesses: aiWeaknesses.text,
            family: aiFamily.text,
            background: aiBackground.text,
            position: aiPosition.text,
            wish: aiWish.text,
            extra: aiExtra.text,
            boundary: aiBoundary.text,
            sourceTags: charPage.aiTags
        })
        setStatus(msg, msg.indexOf("失败") >= 0)
    }

    Connections {
        target: characterController
        function onMatchDone(ok, match, error) {
            if (!ok) {
                charPage.setStatus(error, true)
                return
            }
            charPage.setStatus("AI 设定已生成，可以微调后开始练习生生涯。", false)
        }
        // 生成完成后把 Controller 保存的正式结果同步到页面可编辑字段。
        // 只同步一次；之后用户编辑的是页面字段，最终创建读取页面值。
        function onAiResultChanged() {
            aiAppearance.text = characterController.aiAppearanceStyle
            aiPersonality.text = characterController.aiPersonality
            aiInterests.text = characterController.aiHobbies
            aiStrengths.text = characterController.aiStrengths
            aiWeaknesses.text = characterController.aiWeaknesses
            aiFamily.text = characterController.aiFamily
            aiBackground.text = characterController.aiBackground
            aiPosition.text = characterController.aiPosition
            aiWish.text = characterController.aiWish
            aiExtra.text = characterController.aiExtra
            charPage.aiTags = characterController.aiTags
        }
        function onOpeningMessageDone(ok, text, error) {
            charPage.openingLoading = false
            charPage.openingFallbackUsed = !ok
            charPage.openingText = text
        }
    }

    // ======================================================================
    // Opening message dialog
    // ======================================================================
    Item {
        id: openingOverlay
        anchors.fill: parent
        visible: charPage.openingVisible
        z: 100

        Rectangle {
            anchors.fill: parent
            color: Qt.rgba(0.28, 0.32, 0.45, 0.32)
        }
        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        Rectangle {
            id: openingCard
            width: Math.min(560 * charPage.sp, charPage.width - 64 * charPage.sp)
            height: openingCardCol.implicitHeight + 52 * charPage.sp
            anchors.centerIn: parent
            radius: 24 * charPage.sp
            color: "#FDFCFF"
            border.width: 1
            border.color: Qt.rgba(0.45, 0.5, 0.65, 0.12)

            Column {
                id: openingCardCol
                anchors.fill: parent
                anchors.margins: 26 * charPage.sp
                spacing: 12 * charPage.sp

                Text {
                    text: "✦ 启程之前"
                    color: "#8E88B8"
                    font.pixelSize: 18 * charPage.sp
                    font.bold: true
                    font.family: "Microsoft YaHei UI"
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: charPage.openingLoading ? "正在为你酝酿最初的文字…" : charPage.openingText
                    color: "#3D4963"
                    font.pixelSize: 14 * charPage.sp
                    font.family: "Microsoft YaHei UI"
                    lineHeight: 1.7
                    wrapMode: Text.WordWrap
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                }
                Text {
                    visible: charPage.openingFallbackUsed
                    text: "（生成失败，已使用默认文案）"
                    color: "#9A96B7"
                    font.pixelSize: 10 * charPage.sp
                    font.family: "Microsoft YaHei UI"
                    anchors.horizontalCenter: parent.horizontalCenter
                }

                Item { width: 1; height: 4 * charPage.sp }

                GlassAction {
                    anchors.horizontalCenter: parent.horizontalCenter
                    scaleFactor: charPage.sp
                    label: charPage.openingLoading ? "请稍候…" : "开始创建角色"
                    iconSource: assetBridge.iconUrl("new_character")
                    primary: true
                    enabled: !charPage.openingLoading
                    onClicked: charPage.openingVisible = false
                }
            }
        }
    }

    Component.onCompleted: {
        charPage.openingVisible = true
        charPage.openingLoading = true
        charPage.openingFallbackUsed = false
        charPage.openingText = ""
        characterController.requestOpeningMessage()
    }
}
