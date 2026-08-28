import QtQuick
import QtQuick.Controls
import "../components"

Item {
    id: gamePage

    signal backRequested()
    signal settingsRequested()

    // Design baseline ~1536x864, same clamping as HomePage.
    readonly property real sp: Math.max(0.72, Math.min(1.12, Math.min(width / 1536.0, height / 864.0)))

    // ---- geometry (islands are direct children of the root)
    readonly property real m: 22 * sp
    readonly property real gap: 14 * sp
    readonly property real topH: 48 * sp
    readonly property real timelineH: 66 * sp
    readonly property real midTop: m + topH + gap
    readonly property real midBottom: height - m - timelineH - gap
    readonly property real midH: midBottom - midTop
    readonly property real availableMidW: width - 2 * m
    readonly property real sideW: Math.min(280 * sp, Math.max(170 * sp, (availableMidW - 2 * gap - 320 * sp) / 2))
    readonly property real centerX: m + sideW + gap
    readonly property real centerW: availableMidW - 2 * sideW - 2 * gap
    readonly property real sideX: width - m - sideW

    readonly property real timelineY: height - m - timelineH
    readonly property real timelineChipW: (width - 2 * m - 2 * 14 * sp - 7 * 10 * sp) / 8

    property string activeCategory: ""
    property string activeSub: ""
    property string actionStatus: ""

    // ---- background (existing asset, kept; islands are solid white on top)
    Image {
        anchors.fill: parent
        source: assetBridge.assetUrl("backgrounds/game_bg.png")
        fillMode: Image.PreserveAspectCrop
    }
    Rectangle {
        anchors.fill: parent
        color: "#FFFFFF"
        opacity: 0.06
    }

    // ======================================================================
    // 1. Top island: game time + light navigation
    // ======================================================================
    GlassIsland {
        id: topIsland
        x: gamePage.m
        y: gamePage.m
        width: gamePage.width - 2 * gamePage.m
        height: gamePage.topH
        radius: 18 * gamePage.sp
        glassAlpha: 0.34

        Row {
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 14 * gamePage.sp
            spacing: 14 * gamePage.sp

            Text {
                id: backChip
                text: "‹ 首页"
                color: backHover.hovered ? "#3D4963" : "#7B8498"
                font.pixelSize: 12 * gamePage.sp
                font.family: "Microsoft YaHei UI"
                anchors.verticalCenter: parent.verticalCenter
                HoverHandler { id: backHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: gamePage.backRequested() }
            }

            Rectangle {
                width: 1
                height: 18 * gamePage.sp
                color: Qt.rgba(0.45, 0.5, 0.65, 0.18)
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: "DAY " + gameController.dayNumber
                color: "#56617A"
                font.pixelSize: 15 * gamePage.sp
                font.bold: true
                font.family: "Microsoft YaHei UI"
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: gameController.dateText + " · " + gameController.weekdayText
                color: "#68738C"
                font.pixelSize: 13 * gamePage.sp
                font.family: "Microsoft YaHei UI"
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: gameController.slotText
                color: "#68738C"
                font.pixelSize: 13 * gamePage.sp
                font.family: "Microsoft YaHei UI"
                anchors.verticalCenter: parent.verticalCenter
            }
        }

        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: 10 * gamePage.sp
            spacing: 6 * gamePage.sp

            TopIconButton { iconSource: assetBridge.iconUrl("romance"); label: "关系"; enabled: false; scaleFactor: gamePage.sp }
            TopIconButton { iconSource: assetBridge.iconUrl("diary"); label: "日志"; enabled: false; scaleFactor: gamePage.sp }
            TopIconButton { iconSource: assetBridge.iconUrl("save_archive"); label: "存档"; enabled: false; scaleFactor: gamePage.sp }
            TopIconButton {
                iconSource: assetBridge.iconUrl("settings")
                label: "设置"
                scaleFactor: gamePage.sp
                onClicked: gamePage.settingsRequested()
            }
        }
    }

    // ======================================================================
    // 2. Left island: who she is + long-term skills
    // ======================================================================
    GlassIsland {
        id: leftIsland
        x: gamePage.m
        y: gamePage.midTop
        width: gamePage.sideW
        height: gamePage.midH
        radius: 20 * gamePage.sp
        glassAlpha: 0.36

        Flickable {
            id: leftFlick
            anchors.fill: parent
            anchors.margins: 16 * gamePage.sp
            contentHeight: leftCol.height
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; visible: false }

            Column {
                id: leftCol
                width: leftFlick.width
                spacing: 10 * gamePage.sp

                Row {
                    width: parent.width
                    spacing: 10 * gamePage.sp
                    Item {
                        width: 54 * gamePage.sp
                        height: 54 * gamePage.sp
                        implicitWidth: 54 * gamePage.sp
                        implicitHeight: 54 * gamePage.sp
                        anchors.verticalCenter: parent.verticalCenter
                        Rectangle {
                            anchors.fill: parent
                            radius: width / 2
                            color: Qt.rgba(0.97, 0.93, 0.94, 0.55)
                        }
                        Rectangle {
                            anchors.centerIn: parent
                            width: 48 * gamePage.sp
                            height: 48 * gamePage.sp
                            radius: width / 2
                            clip: true
                            Image {
                                anchors.fill: parent
                                fillMode: Image.PreserveAspectCrop
                                sourceSize: Qt.size(48 * gamePage.sp, 48 * gamePage.sp)
                                source: gameController.avatar !== ""
                                       ? assetBridge.assetUrl(gameController.avatar)
                                       : assetBridge.iconUrl("app_logo")
                            }
                        }
                    }
                    Column {
                        width: parent.width - 64 * gamePage.sp
                        spacing: 1
                        anchors.verticalCenter: parent.verticalCenter
                        Text {
                            text: gameController.stageName || gameController.realName || "练习生"
                            color: "#3D4963"
                            font.pixelSize: 16 * gamePage.sp
                            font.bold: true
                            font.family: "Microsoft YaHei UI"
                            elide: Text.ElideRight
                            width: parent.width
                        }
                        Text {
                            text: gameController.realName
                            visible: gameController.realName !== "" && gameController.realName !== gameController.stageName
                            color: "#8C88A6"
                            font.pixelSize: 11 * gamePage.sp
                            font.family: "Microsoft YaHei UI"
                            elide: Text.ElideRight
                            width: parent.width
                        }
                        Text {
                            text: gameController.ageText + " · " + gameController.nationality
                            color: "#68738C"
                            font.pixelSize: 11 * gamePage.sp
                            font.family: "Microsoft YaHei UI"
                            elide: Text.ElideRight
                            width: parent.width
                        }
                    }
                }

                Row {
                    width: parent.width
                    spacing: 6 * gamePage.sp
                    Text {
                        text: "练习生等级"
                        color: "#7B8498"
                        font.pixelSize: 11 * gamePage.sp
                        font.family: "Microsoft YaHei UI"
                    }
                    Text {
                        text: "Lv." + gameController.trainingLevel
                        color: "#56617A"
                        font.pixelSize: 11 * gamePage.sp
                        font.bold: true
                        font.family: "Microsoft YaHei UI"
                    }
                }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Qt.rgba(0.35, 0.4, 0.55, 0.12)
                }

                Text {
                    text: "长期能力"
                    color: "#56617A"
                    font.pixelSize: 12 * gamePage.sp
                    font.bold: true
                    font.family: "Microsoft YaHei UI"
                }

                SkillRow { width: leftCol.width; scaleFactor: gamePage.sp; label: gameController.skillsModel.length > 0 ? gameController.skillsModel[0].label : ""; valueText: gameController.skillsModel.length > 0 && gameController.skillsModel[0].unlocked ? String(gameController.skillsModel[0].value) : "未解锁"; muted: !(gameController.skillsModel.length > 0 && gameController.skillsModel[0].unlocked) }
                SkillRow { width: leftCol.width; scaleFactor: gamePage.sp; label: gameController.skillsModel.length > 1 ? gameController.skillsModel[1].label : ""; valueText: gameController.skillsModel.length > 1 && gameController.skillsModel[1].unlocked ? String(gameController.skillsModel[1].value) : "未解锁"; muted: !(gameController.skillsModel.length > 1 && gameController.skillsModel[1].unlocked) }
                SkillRow { width: leftCol.width; scaleFactor: gamePage.sp; label: gameController.skillsModel.length > 2 ? gameController.skillsModel[2].label : ""; valueText: gameController.skillsModel.length > 2 && gameController.skillsModel[2].unlocked ? String(gameController.skillsModel[2].value) : "未解锁"; muted: !(gameController.skillsModel.length > 2 && gameController.skillsModel[2].unlocked) }
                SkillRow { width: leftCol.width; scaleFactor: gamePage.sp; label: gameController.skillsModel.length > 3 ? gameController.skillsModel[3].label : ""; valueText: gameController.skillsModel.length > 3 && gameController.skillsModel[3].unlocked ? String(gameController.skillsModel[3].value) : "未解锁"; muted: !(gameController.skillsModel.length > 3 && gameController.skillsModel[3].unlocked) }
                SkillRow { width: leftCol.width; scaleFactor: gamePage.sp; label: gameController.skillsModel.length > 4 ? gameController.skillsModel[4].label : ""; valueText: gameController.skillsModel.length > 4 && gameController.skillsModel[4].unlocked ? String(gameController.skillsModel[4].value) : "未解锁"; muted: !(gameController.skillsModel.length > 4 && gameController.skillsModel[4].unlocked) }
                SkillRow { width: leftCol.width; scaleFactor: gamePage.sp; label: gameController.skillsModel.length > 5 ? gameController.skillsModel[5].label : ""; valueText: gameController.skillsModel.length > 5 && gameController.skillsModel[5].unlocked ? String(gameController.skillsModel[5].value) : "未解锁"; muted: !(gameController.skillsModel.length > 5 && gameController.skillsModel[5].unlocked) }
                SkillRow { width: leftCol.width; scaleFactor: gamePage.sp; label: gameController.skillsModel.length > 6 ? gameController.skillsModel[6].label : ""; valueText: gameController.skillsModel.length > 6 && gameController.skillsModel[6].unlocked ? String(gameController.skillsModel[6].value) : "未解锁"; muted: !(gameController.skillsModel.length > 6 && gameController.skillsModel[6].unlocked) }
                SkillRow { width: leftCol.width; scaleFactor: gamePage.sp; label: gameController.skillsModel.length > 7 ? gameController.skillsModel[7].label : ""; valueText: gameController.skillsModel.length > 7 && gameController.skillsModel[7].unlocked ? String(gameController.skillsModel[7].value) : "未解锁"; muted: !(gameController.skillsModel.length > 7 && gameController.skillsModel[7].unlocked) }

                Item { width: 1; height: 2 * gamePage.sp }
            }
        }
    }

    // ======================================================================
    // 3. Right island: current body / mind state
    // ======================================================================
    GlassIsland {
        id: rightIsland
        x: gamePage.sideX
        y: gamePage.midTop
        width: gamePage.sideW
        height: gamePage.midH
        radius: 20 * gamePage.sp
        glassAlpha: 0.36

        Flickable {
            id: rightFlick
            anchors.fill: parent
            anchors.margins: 16 * gamePage.sp
            contentHeight: rightCol.height
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; visible: false }

            Column {
                id: rightCol
                width: rightFlick.width
                spacing: 8 * gamePage.sp

                Text {
                    text: "当前状态"
                    color: "#56617A"
                    font.pixelSize: 12 * gamePage.sp
                    font.bold: true
                    font.family: "Microsoft YaHei UI"
                }

                Text {
                    text: "身体状态"
                    color: "#8C88A6"
                    font.pixelSize: 10 * gamePage.sp
                    font.family: "Microsoft YaHei UI"
                }

                CondRow { width: rightCol.width; scaleFactor: gamePage.sp; label: gameController.conditionModel.length > 0 ? gameController.conditionModel[0].label : ""; value: gameController.conditionModel.length > 0 ? gameController.conditionModel[0].value : 0; isBody: true }
                CondRow { width: rightCol.width; scaleFactor: gamePage.sp; label: gameController.conditionModel.length > 1 ? gameController.conditionModel[1].label : ""; value: gameController.conditionModel.length > 1 ? gameController.conditionModel[1].value : 0; isBody: true }
                CondRow { width: rightCol.width; scaleFactor: gamePage.sp; label: gameController.conditionModel.length > 2 ? gameController.conditionModel[2].label : ""; value: gameController.conditionModel.length > 2 ? gameController.conditionModel[2].value : 0; isBody: true }
                CondRow { width: rightCol.width; scaleFactor: gamePage.sp; label: gameController.conditionModel.length > 3 ? gameController.conditionModel[3].label : ""; value: gameController.conditionModel.length > 3 ? gameController.conditionModel[3].value : 0; isBody: true }
                CondRow { width: rightCol.width; scaleFactor: gamePage.sp; label: gameController.conditionModel.length > 4 ? gameController.conditionModel[4].label : ""; value: gameController.conditionModel.length > 4 ? gameController.conditionModel[4].value : 0; isBody: true }
                CondRow { width: rightCol.width; scaleFactor: gamePage.sp; label: gameController.conditionModel.length > 5 ? gameController.conditionModel[5].label : ""; value: gameController.conditionModel.length > 5 ? gameController.conditionModel[5].value : 0; isBody: false }
                CondRow { width: rightCol.width; scaleFactor: gamePage.sp; label: gameController.conditionModel.length > 6 ? gameController.conditionModel[6].label : ""; value: gameController.conditionModel.length > 6 ? gameController.conditionModel[6].value : 0; isBody: false }
                CondRow { width: rightCol.width; scaleFactor: gamePage.sp; label: gameController.conditionModel.length > 7 ? gameController.conditionModel[7].label : ""; value: gameController.conditionModel.length > 7 ? gameController.conditionModel[7].value : 0; isBody: false }

                Rectangle {
                    width: parent.width
                    height: 1
                    color: Qt.rgba(0.35, 0.4, 0.55, 0.12)
                }

                Text {
                    text: "练习生身份"
                    color: "#56617A"
                    font.pixelSize: 12 * gamePage.sp
                    font.bold: true
                    font.family: "Microsoft YaHei UI"
                }
                Row {
                    width: parent.width
                    spacing: 6 * gamePage.sp
                    Text {
                        text: "训练等级"
                        color: "#7B8498"
                        font.pixelSize: 11 * gamePage.sp
                        font.family: "Microsoft YaHei UI"
                    }
                    Text {
                        text: "Lv." + gameController.trainingLevel
                        color: "#56617A"
                        font.pixelSize: 11 * gamePage.sp
                        font.bold: true
                        font.family: "Microsoft YaHei UI"
                    }
                }
                Row {
                    width: parent.width
                    spacing: 6 * gamePage.sp
                    Text {
                        text: "最新月评"
                        color: "#7B8498"
                        font.pixelSize: 11 * gamePage.sp
                        font.family: "Microsoft YaHei UI"
                    }
                    Text {
                        text: gameController.evaluationText
                        color: gameController.evaluationText === "尚未进行" ? "#9A96B7" : "#56617A"
                        font.pixelSize: 11 * gamePage.sp
                        font.bold: gameController.evaluationText !== "尚未进行"
                        font.family: "Microsoft YaHei UI"
                    }
                }
            }
        }
    }

    // ======================================================================
    // 4. Center: narrative island (visual core)
    // ======================================================================
    GlassIsland {
        id: narrativeIsland
        x: gamePage.centerX
        y: gamePage.midTop
        width: gamePage.centerW
        height: gamePage.midBottom - actionArea.height - gamePage.gap - gamePage.midTop
        radius: 20 * gamePage.sp
        glassAlpha: 0.50

        Column {
            anchors.fill: parent
            anchors.margins: 20 * gamePage.sp
            spacing: 12 * gamePage.sp

            Row {
                width: parent.width
                spacing: 10 * gamePage.sp

                Rectangle {
                    height: 26 * gamePage.sp
                    radius: 13 * gamePage.sp
                    color: Qt.rgba(0.9, 0.88, 0.97, 0.5)
                    width: contextChipText.implicitWidth + 24 * gamePage.sp
                    Text {
                        id: contextChipText
                        anchors.centerIn: parent
                        text: gameController.contextText
                        color: "#6A6684"
                        font.pixelSize: 12 * gamePage.sp
                        font.family: "Microsoft YaHei UI"
                    }
                }
                Text {
                    text: gameController.slotText
                    color: "#9A96B7"
                    font.pixelSize: 12 * gamePage.sp
                    font.family: "Microsoft YaHei UI"
                    anchors.verticalCenter: parent.verticalCenter
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Qt.rgba(0.35, 0.4, 0.55, 0.12)
            }

            Flickable {
                id: narrativeFlick
                width: parent.width
                height: parent.height - 51 * gamePage.sp
                contentHeight: narrativeText.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                Text {
                    id: narrativeText
                    width: narrativeFlick.width
                    text: gameController.narrativeText
                    color: "#3D4963"
                    font.pixelSize: 13.5 * gamePage.sp
                    font.family: "Microsoft YaHei UI"
                    lineHeight: 1.6
                    wrapMode: Text.WordWrap
                }
            }
        }
    }

    // ======================================================================
    // 5. Action area (attached under the narrative island)
    // ======================================================================
    Item {
        id: actionArea
        x: gamePage.centerX
        y: gamePage.midBottom - actionArea.height
        width: gamePage.centerW
        height: Math.min(210 * gamePage.sp, actionCol.implicitHeight + 16 * gamePage.sp)

        Column {
            id: actionCol
            anchors.fill: parent
            spacing: 8 * gamePage.sp

            Text {
                text: gamePage.actionHint()
                visible: text !== ""
                color: "#7B8498"
                font.pixelSize: 11 * gamePage.sp
                font.family: "Microsoft YaHei UI"
                width: parent.width
                wrapMode: Text.WordWrap
            }

            Flow {
                width: parent.width
                spacing: 8 * gamePage.sp
                visible: gameController.actionsModel.length > 0 && !gameController.currentSlotAssigned

                ActionChip {
                    scaleFactor: gamePage.sp
                    label: "训练"
                    selected: gamePage.activeCategory === "TRAIN"
                    onClicked: gamePage.toggleCategory("TRAIN")
                }
                ActionChip {
                    scaleFactor: gamePage.sp
                    label: "社交"
                    selected: gamePage.activeCategory === "SOCIAL"
                    onClicked: gamePage.toggleCategory("SOCIAL")
                }
                ActionChip {
                    scaleFactor: gamePage.sp
                    label: "恢复"
                    selected: gamePage.activeCategory === "RECOVER"
                    onClicked: gamePage.toggleCategory("RECOVER")
                }
                ActionChip {
                    scaleFactor: gamePage.sp
                    label: "探索"
                    selected: gamePage.activeCategory === "EXPLORE"
                    onClicked: gamePage.toggleCategory("EXPLORE")
                }
                ActionChip {
                    scaleFactor: gamePage.sp
                    label: "个人事务"
                    selected: gamePage.activeCategory === "PERSONAL"
                    onClicked: gamePage.toggleCategory("PERSONAL")
                }
            }

            Flow {
                width: parent.width
                spacing: 8 * gamePage.sp
                visible: gamePage.activeCategory === "TRAIN" && !gameController.currentSlotAssigned

                Repeater {
                    model: gameController.trainSkillsModel
                    ActionChip {
                        scaleFactor: gamePage.sp
                        label: modelData.label
                        selected: gamePage.activeSub === modelData.key
                        onClicked: gamePage.activeSub = (gamePage.activeSub === modelData.key) ? "" : modelData.key
                    }
                }
            }

            Flow {
                width: parent.width
                spacing: 8 * gamePage.sp
                visible: gamePage.activeCategory === "EXPLORE" && !gameController.currentSlotAssigned

                Repeater {
                    model: gameController.exploreDomainsModel
                    ActionChip {
                        scaleFactor: gamePage.sp
                        label: modelData.label
                        selected: gamePage.activeSub === modelData.key
                        onClicked: gamePage.activeSub = (gamePage.activeSub === modelData.key) ? "" : modelData.key
                    }
                }
            }

            Flow {
                width: parent.width
                spacing: 8 * gamePage.sp
                visible: gamePage.activeCategory === "PERSONAL" && !gameController.currentSlotAssigned

                Repeater {
                    model: gameController.personalActionsModel
                    ActionChip {
                        scaleFactor: gamePage.sp
                        label: modelData.label
                        selected: gamePage.activeSub === modelData.key
                        onClicked: gamePage.activeSub = (gamePage.activeSub === modelData.key) ? "" : modelData.key
                    }
                }
            }

            Flow {
                width: parent.width
                spacing: 8 * gamePage.sp
                visible: gamePage.activeCategory === "SOCIAL" && !gameController.currentSlotAssigned

                Repeater {
                    model: gameController.npcsModel
                    ActionChip {
                        scaleFactor: gamePage.sp
                        label: modelData.label
                        selected: gamePage.activeSub === modelData.key
                        onClicked: gamePage.activeSub = (gamePage.activeSub === modelData.key) ? "" : modelData.key
                    }
                }
            }

            GlassAction {
                visible: gamePage.activeCategory !== "" && !gameController.currentSlotAssigned && gamePage.selectionComplete()
                scaleFactor: gamePage.sp
                label: "安排到当前时间格"
                iconSource: assetBridge.iconUrl("save_archive")
                primary: true
                onClicked: {
                    gamePage.actionStatus = gameController.assignAction(gamePage.activeCategory, gamePage.activeSub)
                }
            }

            Text {
                visible: gamePage.actionStatus !== ""
                text: gamePage.actionStatus
                color: gamePage.actionStatus.indexOf("失败") >= 0 ? "#D86B7A" : "#7FAE9A"
                font.pixelSize: 11 * gamePage.sp
                font.family: "Microsoft YaHei UI"
                width: parent.width
                wrapMode: Text.WordWrap
            }

            Text {
                visible: gameController.currentSlotAssigned
                text: "本格已安排：" + gameController.currentSlotActionText + "。行动已确定，完成后进入下一时间格。"
                color: "#68738C"
                font.pixelSize: 12 * gamePage.sp
                font.family: "Microsoft YaHei UI"
                width: parent.width
                wrapMode: Text.WordWrap
            }
        }
    }

    function toggleCategory(key) {
        if (gamePage.activeCategory === key) {
            gamePage.activeCategory = ""
        } else {
            gamePage.activeCategory = key
            gamePage.activeSub = ""
            gamePage.actionStatus = ""
        }
    }

    function selectionComplete() {
        if (gamePage.activeCategory === "RECOVER")
            return true
        if (gamePage.activeCategory === "TRAIN"
                || gamePage.activeCategory === "EXPLORE"
                || gamePage.activeCategory === "PERSONAL"
                || gamePage.activeCategory === "SOCIAL")
            return gamePage.activeSub !== ""
        return false
    }

    function actionHint() {
        if (gameController.currentSlotAssigned)
            return ""
        if (gamePage.activeCategory === "TRAIN")
            return "选择要训练的方向："
        if (gamePage.activeCategory === "EXPLORE")
            return "探索尚未入门的方向："
        if (gamePage.activeCategory === "SOCIAL")
            return "选择要和谁待在一起："
        if (gamePage.activeCategory === "RECOVER")
            return "恢复行动不需要额外选择，直接安排即可："
        if (gamePage.activeCategory === "PERSONAL")
            return "选择要处理的个人事务："
        return gameController.actionHintText
    }

    // ======================================================================
    // 6. Bottom: today's 8-slot timeline
    // ======================================================================
    GlassIsland {
        id: timelineIsland
        x: gamePage.m
        y: gamePage.timelineY
        width: gamePage.width - 2 * gamePage.m
        height: gamePage.timelineH
        radius: 18 * gamePage.sp
        glassAlpha: 0.32

        Row {
            anchors.fill: parent
            anchors.margins: 14 * gamePage.sp
            spacing: 10 * gamePage.sp

            Repeater {
                model: gameController.slotsModel
                SlotChip {
                    width: gamePage.timelineChipW
                    height: parent.height
                    scaleFactor: gamePage.sp
                    label: modelData.label
                    indexLabel: "第" + (modelData.index + 1) + "格"
                    completed: modelData.completed
                    current: modelData.current
                }
            }
        }
    }

    // ---- generic state guard ---------------------------------------------
    Text {
        visible: !gameController.hasLoaded
        anchors.centerIn: parent
        text: gameController.loadErrorText
        color: "#D86B7A"
        font.pixelSize: 13 * gamePage.sp
        font.family: "Microsoft YaHei UI"
    }
}
