// Utilities
import { describe, expect, it } from '@jest/globals';

import { callWithErrorHandling, callWithAsyncErrorHandling } from '../errorHandling';

describe('errorHandling', () => {
  it('runs functions normally', () => {
    const res = callWithErrorHandling(() => 123);
    expect(res).toBe(123);
  });

  it('accepts args', () => {
    const res = callWithErrorHandling(
      (arg1, arg2, ...args) => [arg1, arg2, args],
      [{ a: 'b', 123: 456 }, null, 1, 2, 3]
    );

    expect(res).toEqual([{ a: 'b', 123: 456 }, null, [1, 2, 3]]);
  });

  it('recovers from errors', () => {
    const res = callWithErrorHandling(
      (arg1, arg2, ...args) => {
        throw Error('Oops!');
      },
      [{ a: 'b', 123: 456 }, null, 1, 2, 3]
    );

    expect(res).toBe(undefined);
  });

  it('async single fn', () => {
    const res = callWithAsyncErrorHandling(async (arg1) => [arg1], [{ a: 'b', 123: 456 }]);

    expect(res).resolves.toEqual([{ a: 'b', 123: 456 }]);
  });

  it('async multiple fns', () => {
    const res = callWithAsyncErrorHandling(
      [async (arg1) => [arg1], async () => [2, 3, 4]],
      [{ a: 'b', 123: 456 }]
    );

    expect(Promise.all(res)).resolves.toEqual([[{ a: 'b', 123: 456 }], [2, 3, 4]]);
  });

  it('async recovers from errors', () => {
    const res = callWithAsyncErrorHandling(
      [
        async (arg1) => {
          throw Error('Oops!');
        },
        async () => {
          throw Error('Oops!');
        },
      ],
      [{ a: 'b', 123: 456 }]
    );

    expect(res).toHaveLength(2);
    expect(res[0]).rejects.toStrictEqual(Error('Oops!'));
    expect(res[1]).rejects.toStrictEqual(Error('Oops!'));
  });
});
