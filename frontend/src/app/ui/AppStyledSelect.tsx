import type { ComponentProps } from "react";
import StyledSelect from "../../mystic_auth/ui/filters/StyledSelect";

type Props = ComponentProps<typeof StyledSelect> & { w?: string };

export default function AppStyledSelect({ w, ...props }: Props) {
    void w;
    return <StyledSelect {...props} />;
}
