import {
  ComboBox,
  // @ts-ignore
} from '@carbon/react';
import { ProcessGroupLite, ProcessModel } from '../interfaces';

type OwnProps = {
  onChange: (..._args: any[]) => any;
  processModels: ProcessModel[];
  selectedItem?: ProcessModel | null;
  titleText?: string;
};

export default function ProcessModelSearch({
  processModels,
  selectedItem,
  onChange,
  titleText = 'Process',
}: OwnProps) {
  const getParentGroupsDisplayName = (processModel: ProcessModel) => {
    if (processModel.parent_groups) {
      return processModel.parent_groups
        .map((parentGroup: ProcessGroupLite) => {
          return parentGroup.display_name;
        })
        .join(' / ');
    }
    return '';
  };

  const getProcessModelLabelForDisplay = (processModel: ProcessModel) => {
    return `${processModel.display_name} (${processModel.id})`;
  };

  const getProcessModelLabelForSearch = (processModel: ProcessModel) => {
    return `${processModel.display_name} ${
      processModel.id
    } ${getParentGroupsDisplayName(processModel)}`;
  };

  const shouldFilterProcessModel = (options: any) => {
    const processModel: ProcessModel = options.item;
    let { inputValue } = options;
    if (!inputValue) {
      inputValue = '';
    }
    const inputValueArray = inputValue.split(' ');
    const processModelLowerCase =
      getProcessModelLabelForSearch(processModel).toLowerCase();

    return inputValueArray.every((i: any) => {
      return processModelLowerCase.includes((i || '').toLowerCase());
    });
  };
  return (
    <ComboBox
      onChange={onChange}
      id="process-model-select"
      data-qa="process-model-selection"
      items={processModels}
      itemToString={(processModel: ProcessModel) => {
        if (processModel) {
          return getProcessModelLabelForDisplay(processModel);
        }
        return null;
      }}
      shouldFilterItem={shouldFilterProcessModel}
      placeholder="Choose a process model"
      titleText={titleText}
      selectedItem={selectedItem}
    />
  );
}
