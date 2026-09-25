/**
 * CSInterface - Adobe CEP Interface Library
 * Minimal implementation for Premiere Pro extensions
 * Based on Adobe CEP 9.0
 */

function CSInterface() {
    this.hostEnvironment = null;
}

/**
 * Evaluates a JavaScript script in the ExtendScript context.
 * @param {string} script - The JavaScript script to evaluate
 * @param {function} callback - Callback function receiving the result
 */
CSInterface.prototype.evalScript = function(script, callback) {
    if (callback === null || callback === undefined) {
        callback = function(result) {};
    }
    
    // Check if we're in CEP environment
    if (typeof __adobe_cep__ !== 'undefined') {
        __adobe_cep__.evalScript(script, callback);
    } else {
        // Development mode - log the script call
        console.log('CEP evalScript (dev mode):', script);
        callback('EvalScript error.');
    }
};

/**
 * Retrieves the host environment object.
 */
CSInterface.prototype.getHostEnvironment = function() {
    if (typeof __adobe_cep__ !== 'undefined') {
        this.hostEnvironment = JSON.parse(__adobe_cep__.getHostEnvironment());
    } else {
        // Development fallback
        this.hostEnvironment = {
            appName: 'DEV',
            appVersion: '0.0',
            appLocale: 'en_US',
            appUILocale: 'en_US',
            appId: 'DEV',
            isAppOffline: false
        };
    }
    return this.hostEnvironment;
};

/**
 * Retrieves the system path.
 * @param {string} pathType - Type of path to retrieve
 */
CSInterface.prototype.getSystemPath = function(pathType) {
    if (typeof __adobe_cep__ !== 'undefined') {
        return __adobe_cep__.getSystemPath(pathType);
    }
    return '';
};

/**
 * Opens a URL in the default browser.
 * @param {string} url - The URL to open
 */
CSInterface.prototype.openURLInDefaultBrowser = function(url) {
    if (typeof __adobe_cep__ !== 'undefined') {
        __adobe_cep__.openURLInDefaultBrowser(url);
    } else {
        window.open(url);
    }
};

/**
 * Registers a callback for a specific event.
 * @param {string} type - Event type
 * @param {function} listener - Event listener callback
 * @param {object} obj - Object context
 */
CSInterface.prototype.addEventListener = function(type, listener, obj) {
    if (typeof __adobe_cep__ !== 'undefined') {
        __adobe_cep__.addEventListener(type, listener, obj);
    }
};

/**
 * Removes a registered callback.
 * @param {string} type - Event type
 * @param {function} listener - Event listener callback
 * @param {object} obj - Object context
 */
CSInterface.prototype.removeEventListener = function(type, listener, obj) {
    if (typeof __adobe_cep__ !== 'undefined') {
        __adobe_cep__.removeEventListener(type, listener, obj);
    }
};

/**
 * Dispatches an event.
 * @param {object} event - Event object to dispatch
 */
CSInterface.prototype.dispatchEvent = function(event) {
    if (typeof __adobe_cep__ !== 'undefined') {
        __adobe_cep__.dispatchEvent(event);
    }
};

/**
 * Closes this extension.
 */
CSInterface.prototype.closeExtension = function() {
    if (typeof __adobe_cep__ !== 'undefined') {
        __adobe_cep__.closeExtension();
    }
};

/**
 * Retrieves extension info.
 * @param {string} extensionId - Extension ID
 */
CSInterface.prototype.getExtensionInfo = function(extensionId) {
    if (typeof __adobe_cep__ !== 'undefined') {
        return JSON.parse(__adobe_cep__.getExtensionInfo(extensionId));
    }
    return {};
};

/**
 * Requests to open an extension.
 * @param {string} extensionId - Extension ID
 * @param {string} startupParams - Startup parameters
 */
CSInterface.prototype.requestOpenExtension = function(extensionId, startupParams) {
    if (typeof __adobe_cep__ !== 'undefined') {
        __adobe_cep__.requestOpenExtension(extensionId, startupParams);
    }
};

/**
 * Gets the current API version.
 */
CSInterface.prototype.getCurrentApiVersion = function() {
    if (typeof __adobe_cep__ !== 'undefined') {
        return JSON.parse(__adobe_cep__.getCurrentApiVersion());
    }
    return { major: 9, minor: 0, micro: 0 };
};

/**
 * Sets the extension's context menu.
 * @param {string} menu - Menu XML string
 * @param {function} callback - Callback for menu item selection
 */
CSInterface.prototype.setContextMenu = function(menu, callback) {
    if (typeof __adobe_cep__ !== 'undefined') {
        __adobe_cep__.setContextMenu(menu, callback);
    }
};

/**
 * Sets the extension's context menu by JSON.
 * @param {string} menu - Menu JSON string
 * @param {function} callback - Callback for menu item selection
 */
CSInterface.prototype.setContextMenuByJSON = function(menu, callback) {
    if (typeof __adobe_cep__ !== 'undefined') {
        __adobe_cep__.setContextMenuByJSON(menu, callback);
    }
};

/**
 * Updates the context menu.
 * @param {string} menu - Updated menu XML/JSON
 */
CSInterface.prototype.updateContextMenuItem = function(menuItemID, enabled, checked) {
    if (typeof __adobe_cep__ !== 'undefined') {
        __adobe_cep__.updateContextMenuItem(menuItemID, enabled, checked);
    }
};

/**
 * Get scale factor of the screen.
 */
CSInterface.prototype.getScaleFactor = function() {
    if (typeof __adobe_cep__ !== 'undefined') {
        return __adobe_cep__.getScaleFactor();
    }
    return 1;
};

/**
 * Set scale factor of the content.
 * @param {number} scaleFactor - Scale factor
 */
CSInterface.prototype.setScaleFactorChangedHandler = function(handler) {
    if (typeof __adobe_cep__ !== 'undefined') {
        __adobe_cep__.setScaleFactorChangedHandler(handler);
    }
};

/**
 * Get the path to the extension folder.
 */
CSInterface.prototype.getExtensionPath = function() {
    if (typeof __adobe_cep__ !== 'undefined') {
        return this.getSystemPath('extension');
    }
    return '.';
};

// System path constants
CSInterface.prototype.EXTENSION_ID = 'extension';

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CSInterface;
}

