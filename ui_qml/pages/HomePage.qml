import QtQuick
import QtQuick.Effects
import "../components"

Item {
    id: home

    // Design baseline ~1536x864; clamp the global scale the same way the
    // Flet home page did. Computed from this item's own size, which equals
    // the window size because of anchors.fill in Main.qml.
    readonly property real scaleFactor: Math.max(0.72, Math.min(1.12, Math.min(width / 1536.0, height / 864.0)))
    readonly property real menuButtonWidth: Math.max(360 * scaleFactor, Math.min(430 * scaleFactor, 0.42 * width))
    readonly property bool showSideCards: width >= 980 && height >= 680
    readonly property bool showQuote: width >= 1100 && height >= 720

    // --- background (existing asset, untouched) ---
    Image {
        id: bgImage
        anchors.fill: parent
        source: assetBridge.assetUrl("backgrounds/home_bg.png")
        fillMode: Image.PreserveAspectCrop
    }
    // very light overlay to help glass / text layering; bg stays bright/dreamy
    Rectangle {
        anchors.fill: parent
        color: "#FFFFFF"
        opacity: 0.04
    }

    // --- shared frosted-glass source -------------------------------------
    // ONE blur of the page background, masked to the menu + toolbar button
    // footprints. The blur is only ever visible inside those buttons (no
    // full-page blur, no external halo). Buttons no longer blur individually,
    // so resize no longer triggers 8 independent crop/blur rebuilds.
    Item {
        id: glassMask
        anchors.fill: parent
        visible: false

        // toolbar footprints (top-right), mirroring the toolbar Row geometry
        Item {
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.rightMargin: 42 * home.scaleFactor
            anchors.topMargin: 30 * home.scaleFactor
            Row {
                spacing: 14 * home.scaleFactor
                Repeater {
                    model: 4
                    Rectangle {
                        width: 92 * home.scaleFactor
                        height: 46 * home.scaleFactor
                        radius: 22 * home.scaleFactor
                        color: "#FFFFFF"
                    }
                }
            }
        }

        // menu footprints (center), mirroring centerGroup / menuCol geometry
        Item {
            anchors.centerIn: parent
            width: home.menuButtonWidth
            height: centerGroup.height
            Column {
                y: titleBlock.height + 34 * home.scaleFactor
                width: home.menuButtonWidth
                spacing: 22 * home.scaleFactor
                Repeater {
                    model: 3
                    Rectangle {
                        width: home.menuButtonWidth
                        height: 76 * home.scaleFactor
                        radius: 17 * home.scaleFactor
                        color: "#FFFFFF"
                    }
                }
            }
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

    // --- bottom row: news card (left) + quote (right) ---
    Item {
        id: bottomRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.leftMargin: 42 * home.scaleFactor
        anchors.rightMargin: 42 * home.scaleFactor
        anchors.bottomMargin: 34 * home.scaleFactor
        height: Math.max(newsCard.visible ? newsCard.height : 0,
                         quote.visible ? quote.height : 0)

        GlassPanel {
            id: newsCard
            scaleFactor: home.scaleFactor
            width: 410 * home.scaleFactor
            height: 172 * home.scaleFactor
            padding: 22 * home.scaleFactor
            glassAlpha: 0.34
            shadowAlpha: 0.06
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            visible: home.showSideCards

            Column {
                anchors.fill: parent
                spacing: 6 * home.scaleFactor
                Row {
                    spacing: 8 * home.scaleFactor
                    Image {
                        source: assetBridge.iconUrl("diary")
                        width: 22 * home.scaleFactor
                        height: 22 * home.scaleFactor
                        fillMode: Image.PreserveAspectFit
                        sourceSize: Qt.size(22 * home.scaleFactor, 22 * home.scaleFactor)
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: "星光日报"
                        color: "#6A6684"
                        font.pixelSize: 16 * home.scaleFactor
                        font.bold: true
                        font.family: "Microsoft YaHei UI"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                Text { text: "今日行程更新"; color: "#7D8CA0"; font.pixelSize: 13 * home.scaleFactor; font.family: "Microsoft YaHei UI" }
                Text { text: "· 个人档案：开启角色创建"; color: "#7D8CA0"; font.pixelSize: 13 * home.scaleFactor; font.family: "Microsoft YaHei UI" }
                Text { text: "· 存档：支持正式回合记录"; color: "#7D8CA0"; font.pixelSize: 13 * home.scaleFactor; font.family: "Microsoft YaHei UI" }
                Text { text: "· UI：主页视觉重制中"; color: "#7D8CA0"; font.pixelSize: 13 * home.scaleFactor; font.family: "Microsoft YaHei UI" }
            }
        }

        Image {
            id: quote
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: 8 * home.scaleFactor
            anchors.bottomMargin: 6 * home.scaleFactor
            visible: home.showQuote
            source: assetBridge.assetUrl("images/home_quote_clean.png")
            width: 455 * home.scaleFactor
            height: implicitWidth > 0 ? width * implicitHeight / implicitWidth : width
            fillMode: Image.PreserveAspectFit
            opacity: 0.98
        }
    }

    // --- top row: profile card (left) + toolbar (right) ---
    Item {
        id: topRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.leftMargin: 42 * home.scaleFactor
        anchors.rightMargin: 42 * home.scaleFactor
        anchors.topMargin: 30 * home.scaleFactor
        height: Math.max(profileCard.visible ? profileCard.height : 0,
                        toolbar.height)

        GlassPanel {
            id: profileCard
            scaleFactor: home.scaleFactor
            width: 320 * home.scaleFactor
            height: 126 * home.scaleFactor
            glassAlpha: 0.34
            shadowAlpha: 0.06
            anchors.left: parent.left
            anchors.top: parent.top
            visible: home.showSideCards

            Row {
                anchors.centerIn: parent
                spacing: 12 * home.scaleFactor
                Item {
                    width: 78 * home.scaleFactor
                    height: 78 * home.scaleFactor
                    anchors.verticalCenter: parent.verticalCenter
                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        color: Qt.rgba(0.97, 0.93, 0.94, 0.55)
                    }
                    Image {
                        anchors.centerIn: parent
                        source: assetBridge.iconUrl("app_logo")
                        width: 72 * home.scaleFactor
                        height: 72 * home.scaleFactor
                        fillMode: Image.PreserveAspectFit
                        sourceSize: Qt.size(72 * home.scaleFactor, 72 * home.scaleFactor)
                    }
                }
                Column {
                    spacing: 1
                    anchors.verticalCenter: parent.verticalCenter
                    Text {
                        text: "星光练习室"
                        color: "#56617A"
                        font.pixelSize: 18 * home.scaleFactor
                        font.bold: true
                        font.family: "Microsoft YaHei UI"
                    }
                    Text {
                        text: "Starlight Practice Room"
                        color: "#8C88A6"
                        font.pixelSize: 11 * home.scaleFactor
                        font.italic: true
                        font.family: "Arial"
                    }
                    Item { width: 1; height: 6 * home.scaleFactor }
                    Text {
                        text: homeController.latestSaveStatusText
                        color: "#7D8CA0"
                        font.pixelSize: 12 * home.scaleFactor
                        font.family: "Microsoft YaHei UI"
                    }
                }
            }
        }

        Row {
            id: toolbar
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: 14 * home.scaleFactor

            GlassToolbarButton {
                iconSource: assetBridge.iconUrl("contract")
                label: "合同"
                scaleFactor: home.scaleFactor
                onClicked: homeController.openContract()
            }
            GlassToolbarButton {
                iconSource: assetBridge.iconUrl("diary")
                label: "日记"
                scaleFactor: home.scaleFactor
                onClicked: homeController.openDiary()
            }
            GlassToolbarButton {
                iconSource: assetBridge.iconUrl("schedule")
                label: "行程"
                scaleFactor: home.scaleFactor
                onClicked: homeController.openSchedule()
            }
            GlassToolbarButton {
                iconSource: assetBridge.iconUrl("settings")
                label: "设置"
                scaleFactor: home.scaleFactor
                onClicked: homeController.openSettings()
            }
        }
    }

    // --- center: title + main menu ---
    Item {
        id: centerGroup
        anchors.centerIn: parent
        width: Math.max(titleBlock.width, menuCol.width)
        height: titleBlock.height + 34 * home.scaleFactor + menuCol.height

        Item {
            id: titleBlock
            anchors.top: parent.top
            anchors.horizontalCenter: parent.horizontalCenter
            width: 480 * home.scaleFactor
            height: t1.height + t2.height + t3.height + t4.height

            Text {
                id: t1
                anchors.top: parent.top
                anchors.horizontalCenter: parent.horizontalCenter
                text: "✦"
                color: "#B7A6D8"
                font.pixelSize: 36 * home.scaleFactor
                horizontalAlignment: Text.AlignHCenter
            }
            Text {
                id: t2
                anchors.top: t1.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                text: "星光练习室"
                color: "#8E88B8"
                font.pixelSize: 64 * home.scaleFactor
                font.bold: true
                font.family: "Microsoft YaHei UI"
                horizontalAlignment: Text.AlignHCenter
            }
            Text {
                id: t3
                anchors.top: t2.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Starlight Practice Room"
                color: "#9A96B7"
                font.pixelSize: 18 * home.scaleFactor
                font.italic: true
                font.family: "Arial"
                horizontalAlignment: Text.AlignHCenter
            }
            Text {
                id: t4
                anchors.top: t3.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                text: "KPOP 练习生模拟器"
                color: "#7D8CA0"
                font.pixelSize: 16 * home.scaleFactor
                font.family: "Microsoft YaHei UI"
                horizontalAlignment: Text.AlignHCenter
            }
        }

        Column {
            id: menuCol
            anchors.top: titleBlock.bottom
            anchors.topMargin: 34 * home.scaleFactor
            anchors.horizontalCenter: parent.horizontalCenter
            width: home.menuButtonWidth
            spacing: 22 * home.scaleFactor

            GlassMenuButton {
                width: home.menuButtonWidth
                scaleFactor: home.scaleFactor
                title: "继续旅程"
                subtitle: "读取最近一次存档，回到练习室"
                english: "CONTINUE"
                iconSource: assetBridge.iconUrl("app_logo")
                disabled: !homeController.hasLatestSave
                onClicked: homeController.continueGame()
            }
            GlassMenuButton {
                width: home.menuButtonWidth
                scaleFactor: home.scaleFactor
                title: "新的人生"
                subtitle: "创建角色，从第一天报到开始"
                english: "NEW GAME"
                iconSource: assetBridge.iconUrl("new_character")
                onClicked: homeController.newGame()
            }
            GlassMenuButton {
                width: home.menuButtonWidth
                scaleFactor: home.scaleFactor
                title: "读取存档"
                subtitle: "查看所有保存的故事线"
                english: "LOAD GAME"
                iconSource: assetBridge.iconUrl("save_archive")
                onClicked: homeController.loadGame()
            }
        }
    }
}
