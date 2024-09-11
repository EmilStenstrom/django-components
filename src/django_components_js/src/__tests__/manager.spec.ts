// Utilities
import { describe, expect, it } from '@jest/globals';

import { ComponentContext, createComponentsManager } from '../manager';

describe('componentsManager', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
    document.head.innerHTML = '';
  });

  describe('loadScript', () => {
    it('loads JS scripts', () => {
      const manager = createComponentsManager();

      // Adds a script the first time
      manager.loadScript('js', "<script src='/one/two'></script>");
      expect(document.body.innerHTML).toBe('<script src="/one/two"></script>');

      // Does not add it the second time
      manager.loadScript('js', "<script src='/one/two'></script>");
      expect(document.body.innerHTML).toBe('<script src="/one/two"></script>');

      // Adds different script
      manager.loadScript('js', "<script src='/four/three'></script>");
      expect(document.body.innerHTML).toBe(
        '<script src="/one/two"></script><script src="/four/three"></script>'
      );

      expect(document.head.innerHTML).toBe('');
    });

    it('loads CSS styles', () => {
      const manager = createComponentsManager();

      // Adds a script the first time
      manager.loadScript('css', "<link href='/one/two'>");
      expect(document.head.innerHTML).toBe('<link href="/one/two">');

      // Does not add it the second time
      manager.loadScript('css', "<link herf='/one/two'>");
      expect(document.head.innerHTML).toBe('<link href="/one/two">');

      // Adds different script
      manager.loadScript('css', "<link href='/four/three'>");
      expect(document.head.innerHTML).toBe('<link href="/one/two"><link href="/four/three">');

      expect(document.body.innerHTML).toBe('');
    });

    it('does not load script if marked as loaded', () => {
      const manager = createComponentsManager();

      // Adds a script the first time
      manager.markScriptLoaded('css', '/one/two');
      manager.markScriptLoaded('js', '/one/three');

      manager.loadScript('css', "<link href='/one/two'>");
      expect(document.head.innerHTML).toBe('');

      manager.loadScript('js', "<script src='/one/three'></script>");
      expect(document.body.innerHTML).toBe('');
    });

    it('does not load script if marked as loaded', () => {
      const manager = createComponentsManager();

      // Adds a script the first time
      manager.markScriptLoaded('css', '/one/two');
      manager.markScriptLoaded('js', '/one/three');

      manager.loadScript('css', "<link href='/one/two'>");
      expect(document.head.innerHTML).toBe('');

      manager.loadScript('js', "<script src='/one/three'></script>");
      expect(document.body.innerHTML).toBe('');
    });
  });

  describe('callComponent', () => {
    it('calls component successfully', () => {
      const manager = createComponentsManager();

      const compName = 'my_comp';
      const compId = '12345';
      const inputHash = 'input-abc';

      document.body.insertAdjacentHTML('beforeend', '<div data-comp-id-12345> abc </div>');

      let capturedCtx: ComponentContext | null = null;
      manager.registerComponent(compName, (ctx) => {
        capturedCtx = ctx;
        return 123;
      });

      manager.registerComponentData(compName, inputHash, () => {
        return { hello: 'world' };
      });

      const res = manager.callComponent(compName, compId, inputHash);

      expect(res).toBe(123);
      expect(capturedCtx).toStrictEqual({
        $data: {
          hello: 'world',
        },
        $els: [document.querySelector('[data-comp-id-12345]')],
        $id: '12345',
        $name: 'my_comp',
      });
    });

    it('calls component successfully async', () => {
      const manager = createComponentsManager();

      const compName = 'my_comp';
      const compId = '12345';
      const inputHash = 'input-abc';

      document.body.insertAdjacentHTML('beforeend', '<div data-comp-id-12345> abc </div>');

      manager.registerComponent(compName, (ctx) => {
        return Promise.resolve(123);
      });

      manager.registerComponentData(compName, inputHash, () => {
        return { hello: 'world' };
      });

      const res = manager.callComponent(compName, compId, inputHash);
      expect(res).resolves.toBe(123);
    });

    it('raises if component element not in DOM', () => {
      const manager = createComponentsManager();

      const compName = 'my_comp';
      const compId = '12345';
      const inputHash = 'input-abc';

      manager.registerComponent(compName, (ctx) => {
        return 123;
      });

      manager.registerComponentData(compName, inputHash, () => {
        return { hello: 'world' };
      });

      expect(() => manager.callComponent(compName, compId, inputHash)).toThrowError(
        Error("[Components] No elements with component ID '12345' found")
      );
    });

    it('raises if input hash not registered', () => {
      const manager = createComponentsManager();

      const compName = 'my_comp';
      const compId = '12345';
      const inputHash = 'input-abc';

      document.body.insertAdjacentHTML('beforeend', '<div data-comp-id-12345> abc </div>');

      manager.registerComponent(compName, (ctx) => {
        return Promise.resolve(123);
      });

      expect(() => manager.callComponent(compName, compId, inputHash)).toThrowError(
        Error("[Components] Cannot find input for hash 'input-abc'")
      );
    });

    it('raises if component is not registered', () => {
      const manager = createComponentsManager();

      const compName = 'my_comp';
      const compId = '12345';
      const inputHash = 'input-abc';

      document.body.insertAdjacentHTML('beforeend', '<div data-comp-id-12345> abc </div>');

      manager.registerComponentData(compName, inputHash, () => {
        return { hello: 'world' };
      });

      expect(() => manager.callComponent(compName, compId, inputHash)).toThrowError(
        Error("[Components] No component registered for name 'my_comp'")
      );
    });
  });
});
