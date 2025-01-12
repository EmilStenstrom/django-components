// We should be able to access the global variables set by the previous components:
// Scripts:
// - script.js               - testMsg
// - script2.js              - testMsg2
// Components:
// - SimpleComponent         - testSimpleComponent
// - SimpleComponentNested   - testSimpleComponentNested
// - OtherComponent          - testOtherComponent

globalThis.checkVars = {
    testSimpleComponent: globalThis.testSimpleComponent,
    testSimpleComponentNested: globalThis.testSimpleComponentNested,
    testOtherComponent: globalThis.testOtherComponent,
    testMsg: globalThis.testMsg,
    testMsg2: globalThis.testMsg2,
};
