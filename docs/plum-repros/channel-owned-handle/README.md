# Channel reply containing an owned native handle fails to link

Reproduced with the Mise-pinned Plum 0.0.41 on Linux/LLVM/Clang:

```
mise exec -- plum check docs/plum-repros/channel-owned-handle
mise exec -- plum build docs/plum-repros/channel-owned-handle -o build/channel-owned-handle
```

Check succeeds; build fails in emitted LLVM IR with an undefined generated
`@plum_str_Reply` helper. The original application reply (`id: Int`,
`image: Option[CoverImage]`) instead failed on `@plum_eq_desktop_CoverReply`.
Replacing only `Option[Image]` with `Option[Int]` builds successfully.
Neither program requests equality or stringification of the reply explicitly.
Expected: either a working channel/select or a source-level diagnostic for an
unsupported payload, rather than invalid generated IR.

The application uses a direct `channel[CoverImage]` successfully. Its single
outstanding request provides the response identity on the UI thread; a null
owned handle reports failure. The native destructor accepts null. This retains
Plum's deterministic cleanup, including a response pending at shutdown.

This is an upstream candidate; no issue has been filed as part of the scrolling
change. The reproduction does not execute or free a native image.
