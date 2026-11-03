type ScrollContainer = Pick<
  HTMLDivElement,
  "clientHeight" | "scrollHeight" | "scrollTop" | "scrollTo"
>;

type AnimationFrameScheduler = Pick<
  Window,
  "cancelAnimationFrame" | "requestAnimationFrame"
>;

const bottomThreshold = 48;

export class ChatScrollFollower {
  private followOutput = true;
  private frame: number | null = null;
  private previousScrollTop: number;

  constructor(
    private readonly container: ScrollContainer,
    private readonly scheduler: AnimationFrameScheduler,
    private readonly prefersReducedMotion: () => boolean,
    private readonly onFollowChange: (following: boolean) => void,
  ) {
    this.previousScrollTop = container.scrollTop;
  }

  readonly handleScroll = () => {
    const currentScrollTop = this.container.scrollTop;
    if (currentScrollTop < this.previousScrollTop) {
      this.setFollowOutput(false);
      this.cancelScheduledScroll();
    } else if (this.isNearBottom()) {
      this.setFollowOutput(true);
    }
    this.previousScrollTop = currentScrollTop;
  };

  readonly followNewOutput = () => {
    if (!this.followOutput || this.frame !== null) {
      return;
    }

    this.frame = this.scheduler.requestAnimationFrame(() => {
      this.frame = null;
      if (this.followOutput) {
        this.scrollToBottom();
      }
    });
  };

  readonly jumpToBottom = () => {
    this.setFollowOutput(true);
    this.cancelScheduledScroll();
    this.scrollToBottom();
  };

  readonly dispose = () => {
    this.cancelScheduledScroll();
  };

  private isNearBottom() {
    return (
      this.container.scrollHeight -
        this.container.clientHeight -
        this.container.scrollTop <=
      bottomThreshold
    );
  }

  private setFollowOutput(following: boolean) {
    if (this.followOutput !== following) {
      this.followOutput = following;
      this.onFollowChange(following);
    }
  }

  private scrollToBottom() {
    this.container.scrollTo({
      top: this.container.scrollHeight,
      behavior: this.prefersReducedMotion() ? "instant" : "smooth",
    });
  }

  private cancelScheduledScroll() {
    if (this.frame !== null) {
      this.scheduler.cancelAnimationFrame(this.frame);
      this.frame = null;
    }
  }
}
