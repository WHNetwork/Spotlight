import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: root
    title: "星光练习室"
    visible: true
    width: 1320
    height: 860
    minimumWidth: 720
    minimumHeight: 540
    color: "#FFFFFF"

    // Simple in-window page routing. home / settings / character / game.
    property string route: "home"

    // Home -> pages: HomePage navigation goes through the global
    // homeController context property (it emits navigationRequested), so this
    // wiring is independent of which page is currently loaded by the Loader.
    Connections {
        target: homeController
        function onNavigationRequested(r) {
            if (r === "settings")
                root.route = "settings"
            else if (r === "new_game")
                root.route = "character"
            else if (r === "continue" || r === "load_game") {
                if (gameController.loadLatestSave())
                    root.route = "game"
            }
            else if (r === "home")
                root.route = "home"
        }
    }

    // Settings / Character / Game -> Home: pages emit backRequested(). Other
    // pages do not have that signal, so ignoreUnknownSignals keeps this single
    // Connections valid for whichever page is loaded.
    Connections {
        target: pageLoader.item
        ignoreUnknownSignals: true
        function onBackRequested() {
            root.route = "home"
        }
        function onSettingsRequested() {
            root.route = "settings"
        }
    }

    // Character creation completed -> enter the main game with the new save.
    Connections {
        target: characterController
        function onCharacterCreated(saveId) {
            if (gameController.loadSave(saveId))
                root.route = "game"
        }
    }

    // File-level lazy load. At startup route is "home", so Main.qml only
    // resolves and parses HomePage.qml. SettingsPage.qml (and its
    // GlassPanel/GlassInput/SegmentedControl/GlassAction dependencies) is NOT
    // parsed until the user opens settings, so a compile/type error there can
    // no longer block application startup. The Loader swaps only on a real
    // route change, never on resize.
    Loader {
        id: pageLoader
        anchors.fill: parent
        source: root.route === "settings"
                ? "pages/SettingsPage.qml"
                : (root.route === "character"
                   ? "pages/CharacterCreationPage.qml"
                   : (root.route === "game"
                      ? "pages/MainGamePage.qml"
                      : "pages/HomePage.qml"))

        // Loaded page roots have no own anchors.fill (it used to be set on the
        // Main instance), so bind their size to the Loader here. This is plain
        // geometry binding, not a create/destroy on resize and not a Timer.
        onLoaded: {
            item.width = Qt.binding(function () { return pageLoader.width })
            item.height = Qt.binding(function () { return pageLoader.height })
        }
    }
}
