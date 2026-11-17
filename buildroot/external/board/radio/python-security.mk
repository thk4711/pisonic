# Loaded via BR2_PACKAGE_OVERRIDE_FILE BEFORE package infrastructure snapshots
# versions and download paths. Keep the stock Buildroot checkout clean.
# These immutable PyPI archives are verified by hashes in patches/<package>/.
# Unlike OVERRIDE_SRCDIR, this preserves download, hash and patch processing.
override PYTHON_PILLOW_VERSION = 13.0.0
override PYTHON_PILLOW_SITE = https://files.pythonhosted.org/packages/ce/a4/9cc30690a394a8305e8be4c9036aa16d0dfddadd09079860b582f562496d
override PYTHON_PILLOW_LICENSE = MIT-CMU
# Preserve the pinned recipe's options, correcting its obsolete libavif key.
override PYTHON_PILLOW_BUILD_OPTS = \
	--skip-dependency-check -Cplatform-guessing=disable -Cimagequant=disable -Craqm=disable \
	$(if $(filter y,$(BR2_PACKAGE_FREETYPE)),-Cfreetype=enable,-Cfreetype=disable) \
	$(if $(filter y,$(BR2_PACKAGE_JPEG)),-Cjpeg=enable,-Cjpeg=disable) \
	$(if $(filter y,$(BR2_PACKAGE_LCMS2)),-Clcms=enable,-Clcms=disable) \
	$(if $(filter y,$(BR2_PACKAGE_LIBAVIF)),-Cavif=enable,-Cavif=disable) \
	$(if $(filter y,$(BR2_PACKAGE_LIBXCB)),-Cxcb=enable,-Cxcb=disable) \
	$(if $(filter y,$(BR2_PACKAGE_OPENJPEG)),-Cjpeg2000=enable,-Cjpeg2000=disable) \
	$(if $(filter y,$(BR2_PACKAGE_TIFF)),-Ctiff=enable,-Ctiff=disable) \
	$(if $(filter yyy,$(BR2_PACKAGE_WEBP)$(BR2_PACKAGE_WEBP_DEMUX)$(BR2_PACKAGE_WEBP_MUX)),-Cwebp=enable,-Cwebp=disable) \
	$(if $(filter y,$(BR2_PACKAGE_ZLIB)),-Czlib=enable,-Czlib=disable)

override PYTHON_REQUESTS_VERSION = 2.34.2
override PYTHON_REQUESTS_SITE = https://files.pythonhosted.org/packages/ac/c3/e2a2b89f2d3e2179abd6d00ebd70bff6273f37fb3e0cc209f48b39d00cbf

override PYTHON_URLLIB3_VERSION = 2.8.0
override PYTHON_URLLIB3_SITE = https://files.pythonhosted.org/packages/e3/05/b17359e1cefb4f909b5e40b1b90a496d987258916dbbf88e842c729f510e

override PYTHON_CERTIFI_VERSION = 2026.10.23
override PYTHON_CERTIFI_SITE = https://files.pythonhosted.org/packages/fd/11/b524cbd9bbdaca58608e4cf4053fd463417549e1959fa8d3aa18319f9555

override PYTHON_IDNA_VERSION = 3.20
override PYTHON_IDNA_SITE = https://files.pythonhosted.org/packages/f5/08/8eea9d4b8302028f3abb2c0813953f7aec26d33b7a8960ed760e65ff29fa
# The license text changed; do not also check it against the old stock hash.
override PYTHON_IDNA_HASH_FILES = $(BR2_EXTERNAL_RADIO_PATH)/board/radio/patches/python-idna/3.20/python-idna.hash
override HOST_PYTHON_IDNA_HASH_FILES = $(PYTHON_IDNA_HASH_FILES)

# The stock 2.4.0 release was yanked for a compatibility regression. Stay in
# the same minor series using its non-yanked maintenance release.
override PYTHON_NUMPY_VERSION = 2.4.6
override PYTHON_NUMPY_SITE = https://files.pythonhosted.org/packages/d0/ad/fed0499ce6a338d2a03ebae59cd15093910c8875328855781952abf6c2fe