import QtQuick

// Lightweight glass action button (test / save). 'primary' gives a slightly
// clearer tint for the save action; no shadow, no halo, no saturated colors.
Item {
    id: root
    signal clicked()
    property string label: ""
    property string iconSource: ""
    property bool primary: false
    property real scaleFactor: 1.0

    implicitWidth: 150 * scaleFactor
    implicitHeight: 42 * scaleFactor
    width: implicitWidth
    height: implicitHeight
    readonly property real radius: 12 * scaleFactor

    opacity: enabled ? 1.0 : 0.5

    readonly property bool _hovered: hover.hovered
    readonly property bool _pressed: tap.pressed

    HoverHandler { id: hover; enabled: root.enabled; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: tap; enabled: root.enabled; onTapped: if (root.enabled) root.clicked() }

    Item {
        id: body
        anchors.fill: parent
        scale: root._pressed ? 0.985 : (root._hovered ? 1.012 : 1.0)
        y: root._hovered ? (root._pressed ? 0 : -1 * scaleFactor) : 0
        transformOrigin: Item.Center
        Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
        Behavior on y { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }

        Rectangle {
            anchors.fill: parent
            radius: root.radius
            color: Qt.rgba(0.945, 0.94, 1.0, root.primary ? (root._hovered ? 0.46 : 0.34) : (root._hovered ? 0.30 : 0.18))
            border.width: 1
            border.color: Qt.rgba(0.98, 0.97, 1.0, root.primary ? (root._hovered ? 0.92 : 0.78) : (root._hovered ? 0.72 : 0.52))
            Behavior on color { ColorAnimation { duration: 150 } }
            Behavior on border.color { ColorAnimation { duration: 150 } }
        }

        Row {
            anchors.centerIn: parent
            spacing: 8 * scaleFactor
            Image {
                source: root.iconSource
                width: 18 * scaleFactor
                height: 18 * scaleFactor
                fillMode: Image.PreserveAspectFit
                sourceSize: Qt.size(24 * scaleFactor, 24 * scaleFactor)
                visible: root.iconSource !== ""
                anchors.verticalCenter: parent.verticalCenter
            }
            Text {
                text: root.label
                color: root.primary ? "#3D4963" : "#4C5670"
                font.pixelSize: 13 * scaleFactor
                font.bold: root.primary
                font.family: "Microsoft YaHei UI"
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
