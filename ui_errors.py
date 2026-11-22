"""Log technical errors with an ID that can be shared from the user interface."""
import logging
from uuid import uuid4


def record_error(path, exc_info):
    code=uuid4().hex[:8].upper()
    handler=None
    logger=logging.Logger('tuhoc.ui')
    try:
        handler=logging.FileHandler(path,encoding='utf-8')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
        logger.addHandler(handler)
        logger.error('Mã lỗi %s',code,exc_info=exc_info)
    except OSError:
        logging.getLogger(__name__).error('Mã lỗi %s',code,exc_info=exc_info)
    finally:
        if handler is not None:
            handler.close()
    return code
