import QtQuick

Item {
    id: root
    signal clicked()

    property string title: ""
    property string subtitle: ""
    property string english: ""
    property url iconSource: ""
    property bool disabled: false
    property real scaleFactor: 1.0

    implicitWidth: 400 * scaleFactor
    implicitHeight: 76 * scaleFactor
    width: implicitWidth
    height: implicitHeight

    // Soft rounded rectangle, not a pill; scales with the UI.
    readonly property real radius: Math.max(10.0, 17.0 * scaleFactor)

    readonly property bool _hovered: hover.hovered
    readonly property bool _pressed: tap.pressed

    // Frosted blur is now provided by HomePage's single shared blur layer
    // (masked to this button's footprint). Here we only keep the glass tint,
    // the highlight edge and the content. No drop shadow, no per-button blur.
    opacity: disabled ? 0.6 : 1.0

    HoverHandler {
        id: hover
        enabled: !root.disabled
        cursorShape: root.disabled ? Qt.ArrowCursor : Qt.PointingHandCursor
    }
    TapHandler {
        id: tap
        enabled: !root.disabled
        onTapped: if (!root.disabled) root.clicked()
    }

    Item {
        id: body
        anchors.fill: parent

        scale: root._pressed ? 0.985 : (root._hovered ? 1.012 : 1.0)
        y: root._hovered ? (root._pressed ? -1 * scaleFactor : -2 * scaleFactor) : 0
        transformOrigin: Item.Center
        Behavior on scale { NumberAnimation { duration: 130; easing.type: Easing.OutCubic } }
        Behavior on y { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }

        // Very light milky lavender tint over the shared frosted blur.
        Rectangle {
            id: tint
            anchors.fill: parent
            radius: root.radius
            color: Qt.rgba(0.945, 0.94, 1.0, root.disabled ? 0.08 : (root._hovered ? 0.26 : 0.16))
            Behavior on color { ColorAnimation { duration: 150 } }
        }

        // Thin cool-white highlight edge.
        Rectangle {
            id: edge
            anchors.fill: parent
            radius: root.radius
            color: "transparent"
            border.width: 1
            border.color: Qt.rgba(0.98, 0.97, 1.0, root.disabled ? 0.30 : (root._hovered ? 0.92 : 0.68))
            Behavior on border.color { ColorAnimation { duration: 150 } }
        }

        Item {
            id: iconBox
            anchors.left: parent.left
            anchors.leftMargin: 22 * scaleFactor
            anchors.verticalCenter: parent.verticalCenter
            width: 48 * scaleFactor
            height: 48 * scaleFactor
            Rectangle {
                anchors.fill: parent
                radius: width / 2
                color: Qt.rgba(0.97, 0.93, 0.94, 0.52)
            }
            Image {
                anchors.centerIn: parent
                source: root.iconSource
                width: 36 * scaleFactor
                height: 36 * scaleFactor
                fillMode: Image.PreserveAspectFit
                sourceSize: Qt.size(48 * scaleFactor, 48 * scaleFactor)
                opacity: root.disabled ? 0.4 : 1.0
                scale: root._hovered ? 1.05 : 1.0
                transformOrigin: Item.Center
                Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
                Behavior on opacity { NumberAnimation { duration: 150 } }
            }
        }

        Text {
            id: english
            anchors.right: parent.right
            anchors.rightMargin: 22 * scaleFactor
            anchors.verticalCenter: parent.verticalCenter
            text: root.english
            color: Qt.rgba(0.40, 0.39, 0.55, root.disabled ? 0.28 : (root._hovered ? 0.88 : 0.62))
            font.pixelSize: 10 * scaleFactor
            font.italic: true
            font.family: "Arial"
            Behavior on color { ColorAnimation { duration: 150 } }
        }

        Column {
            anchors.left: iconBox.right
            anchors.leftMargin: 14 * scaleFactor
            anchors.right: english.left
            anchors.rightMargin: 14 * scaleFactor
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2 * scaleFactor

            Text {
                text: root.title
                color: root.disabled ? "#9AA0B5" : "#414B68"
                font.pixelSize: 18 * scaleFactor
                font.bold: true
                font.family: "Microsoft YaHei UI"
            }
            Text {
                text: root.subtitle
                color: Qt.rgba(0.33, 0.36, 0.47, root.disabled ? 0.55 : 0.92)
                font.pixelSize: 11 * scaleFactor
                font.family: "Microsoft YaHei UI"
            }
        }
    }
}
